"""Strategy: Percent-Away Deviation Band Mean Reversion with Trend Filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD):
Per Google's AI-overview synthesis of QuantVero/VT Markets/LuneFi mean-
reversion guides: a percentage-deviation band around a 50-day SMA
baseline, combined with a 200-day SMA trend filter, identifies
high-probability mean-reversion pullbacks IN THE DIRECTION OF the dominant
trend (not counter-trend against it). Long rule: price dips below the
lower deviation band (-dev_pct% from the 50-SMA) while price remains above
the 200-SMA (i.e. a pullback within an uptrend, not a reversal attempt in
a downtrend). Entry on the close re-crossing back inside the band. Exit
targets the 50-SMA baseline (mean-reversion target) or a hard ATR-multiple
stop-loss below the entry, whichever comes first.

This is structurally related to the already-rejected Kairi Relative Index
(2026-09-04-167, also a %-deviation-from-SMA oscillator with a trend gate)
but differs in its EXIT mechanic: KRI exits on the oscillator recovering
above a threshold or a time-stop, while this strategy exits at a specific
PRICE TARGET (the SMA baseline itself) or an ATR stop-loss, and requires
the price to dip below the band THEN close back inside it (a 2-bar
confirmation) rather than trading purely on the oscillator's own level.

Signal logic
------------
- baseline = SMA(baseline_window).
- lower_band = baseline * (1 - dev_pct).
- trend_up = close > SMA(trend_window).
- Setup: yesterday's close was below lower_band (dip confirmed).
- Entry (long): today's close re-crosses back above lower_band AND
  trend_up holds.
- Exit: close reaches/exceeds the baseline (take-profit at equilibrium),
  OR a hard stop at entry_price - stop_atr_mult*ATR(14) (checked via the
  day's low), OR max_hold_days time-stop, whichever comes first.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    baseline_window: int = 50,
    trend_window: int = 200,
    dev_pct: float = 0.035,
    stop_atr_mult: float = 2.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]

    baseline = close.rolling(baseline_window).mean()
    lower_band = baseline * (1 - dev_pct)
    sma_trend = close.rolling(trend_window).mean()
    trend_up = close.shift(1) > sma_trend.shift(1)
    atr = _atr(df, 14)

    dip_confirmed = close.shift(1) < lower_band.shift(1)
    entry_trigger = (
        (close > lower_band) & dip_confirmed.fillna(False) & trend_up.fillna(False)
    ).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_level = 0.0

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            target_hit = close.iloc[i] >= baseline.iloc[i] if pd.notna(baseline.iloc[i]) else False
            stop_hit = low.iloc[i] <= stop_level
            if target_hit or stop_hit or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
                in_position = True
                entry_idx = i
                entry_price = close.iloc[i]
                atr_now = atr.iloc[i]
                if pd.isna(atr_now):
                    atr_now = 0.0
                stop_level = entry_price - stop_atr_mult * atr_now
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
