"""Strategy: STARC (Stoller Average Range Channel) Bands mean-reversion,
trend-filtered.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-146):
STARC bands (SMA +/- multiplier*ATR envelope, Manning Stoller) provide
dynamic support/resistance. Per Synapse Trading's explainer, the classic
rule is buy near the lower band / sell near the upper band, favored during
an overall uptrend or ranging market (the source explicitly warns against
using this blindly in a downtrend, where price can "walk" the band). This
strategy operationalizes that: long entry when close crosses below the
lower STARC band while price is above a longer-term trend SMA (uptrend
filter, addressing the source's own caveat about band-walking during
downtrends); exit when close crosses back above the SMA basis (mean-
reversion target) or the upper band, the trend filter breaks, or a
max_hold_days time-stop. Distinct from Bollinger Bands (std-based) and
Keltner Channel (EMA+ATR based) already tested in this repo -- STARC uses a
short SMA (5-10 period) + ATR multiple, and is explicitly trend-gated here
per the source's own guidance rather than traded symmetrically in both
regimes.

Signal logic
------------
- Basis = SMA(close, sma_window) [short, 5-10 period per source]
- ATR = Average True Range(atr_window) [~15 period per source]
- STARC upper = Basis + atr_mult * ATR
- STARC lower = Basis - atr_mult * ATR
- Trend filter: close > SMA(close, trend_window) [longer-term uptrend gate]
- Entry (long): close crosses below STARC lower band AND trend filter is
  true (uptrend).
- Exit: close crosses back above the SMA basis, OR close crosses above the
  STARC upper band, OR the trend filter breaks (close <= trend SMA), OR
  max_hold_days elapsed.
- Flat otherwise.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    sma_window: int = 6,
    atr_window: int = 15,
    atr_mult: float = 2.0,
    trend_window: int = 100,
    max_hold_days: int = 10,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    basis = close.rolling(sma_window).mean()
    atr = _atr(df, atr_window)
    upper = basis + atr_mult * atr
    lower = basis - atr_mult * atr
    trend_sma = close.rolling(trend_window).mean()
    uptrend = close > trend_sma

    entry_cross = (close < lower) & (close.shift(1) >= lower.shift(1))
    entry_raw = entry_cross & uptrend

    exit_cross_basis = (close > basis) & (close.shift(1) <= basis.shift(1))
    exit_cross_upper = (close > upper) & (close.shift(1) <= upper.shift(1))
    trend_break = ~uptrend
    exit_signal_raw = exit_cross_basis | exit_cross_upper | trend_break

    entry_arr = entry_raw.fillna(False).to_numpy()
    exit_arr = exit_signal_raw.fillna(True).to_numpy()

    pos_arr = [0] * len(df)
    in_pos = False
    hold_days = 0
    for i in range(len(df)):
        if in_pos:
            hold_days += 1
            if exit_arr[i] or hold_days >= max_hold_days:
                in_pos = False
                hold_days = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if entry_arr[i]:
                in_pos = True
                hold_days = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    sma_window: int = 6,
    atr_window: int = 15,
    atr_mult: float = 2.0,
    trend_window: int = 100,
    max_hold_days: int = 10,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        sma_window=sma_window,
        atr_window=atr_window,
        atr_mult=atr_mult,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
