"""Strategy: Donchian Channel Breakout with ATR Volatility-Expansion Filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD):
Per an academic paper by N. Poluri (SSRN 2026, "Evaluating the Performance
of a Donchian Channel [breakout strategy] enhanced with the ATR-based
volatility regime filter and ATR based [stop-loss]", corroborated by
Google's AI-overview synthesis of the paper's disclosed numeric parameters
after the SSRN full-text was inaccessible without login): a classic
Donchian Channel breakout (long when close breaks above the N-period
highest high) is filtered to only fire when (a) price is in a
long-term uptrend (close > 200-day SMA) and (b) volatility is EXPANDING
(current ATR(14) > its own 50-period moving average), the theory being
that Donchian breakouts are more reliable continuation signals when
volatility itself is expanding (a genuine regime shift) rather than a
one-off spike in an otherwise quiet/contracting market. Exit uses the
opposite (shorter) Donchian channel extreme as a trailing stop, backed by
a hard ATR-multiple stop-loss for tail-risk control.

This combines three components that individually already exist in this
repo (plain Donchian breakout, 200-SMA trend filter, ATR stop-loss) in a
way that has NOT been tested before: the specific ATR(14)-expanding-
relative-to-its-own-50-period-MA volatility filter as a GATE on the
Donchian entry (distinct from the already-tested/accepted GAPO strategy's
"compression-then-breakout" framing, which requires volatility to be LOW
before the breakout, the opposite regime condition).

Signal logic
------------
- entry_channel_high = rolling max of high over the last donchian_entry
  bars (excluding today, i.e. shifted by 1).
- exit_channel_low = rolling min of low over the last donchian_exit bars
  (shorter than donchian_entry, per Turtle-System-style asymmetric
  entry/exit channels).
- Volatility expansion filter: ATR(atr_window) > ATR(atr_window).rolling(
  atr_ma_window).mean() (current ATR above its own trailing average).
- Trend filter: close > SMA(trend_window).
- Entry (long): close breaks above entry_channel_high AND volatility is
  expanding AND in an established uptrend.
- Exit: close breaks below exit_channel_low, OR a hard stop at
  entry_price - stop_atr_mult * ATR(atr_window) (evaluated via the day's
  low), OR max_hold_days time-stop, whichever comes first.

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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
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
    donchian_entry: int = 20,
    donchian_exit: int = 10,
    atr_window: int = 14,
    atr_ma_window: int = 50,
    trend_window: int = 200,
    stop_atr_mult: float = 3.0,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    entry_channel_high = high.rolling(donchian_entry).max().shift(1)
    exit_channel_low = low.rolling(donchian_exit).min().shift(1)
    atr = _atr(df, atr_window)
    atr_ma = atr.rolling(atr_ma_window).mean()
    vol_expanding = atr.shift(1) > atr_ma.shift(1)
    sma_trend = close.rolling(trend_window).mean()
    uptrend = close.shift(1) > sma_trend.shift(1)

    entry_trigger = (
        (close > entry_channel_high) & vol_expanding.fillna(False) & uptrend.fillna(False)
    ).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_level = 0.0

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            exit_channel_hit = low.iloc[i] <= exit_channel_low.iloc[i] if pd.notna(exit_channel_low.iloc[i]) else False
            stop_hit = low.iloc[i] <= stop_level
            if exit_channel_hit or stop_hit or held >= max_hold_days:
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
