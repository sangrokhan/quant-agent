"""Strategy: Disparity Index mean-reversion long entry, gated by an uptrend filter.

Hypothesis (see knowledge_base id 2026-09-06-140):
Per GoCharting's Disparity Index docs
(https://gocharting.com/docs/charting/technical-indicator/oscillators/disparity-index):
"For mean-reversion: when the Disparity Index reaches extreme negative
values in an uptrend, enter long as price returns toward its moving
average." The source explicitly warns: "Do not fade extreme Disparity Index
readings in strong trending markets" (i.e. only fade dips WITHIN an uptrend,
not against a downtrend) and "Always confirm reversions with a candle
pattern or volume signal."

Disparity Index (DI) = 100 * (close - SMA(n)) / SMA(n) -- percentage
distance of price from its moving average.

This is a fresh indicator family for this repo (no prior Disparity Index
strategy tested), distinct from the many previously-tested Bollinger/RSI/
Z-Score mean-reversion strategies since DI is a simple %-distance-from-MA
oscillator rather than a standard-deviation-normalized or RSI-style
momentum measure.

Signal logic
------------
- Uptrend filter: `trend_sma_window`-day SMA is rising (today's value >
  value `trend_slope_lookback` days ago).
- Entry (long): DI (computed against a separate, shorter `di_sma_window`)
  drops to or below `di_entry_threshold` (a negative percentage, e.g. -5%)
  WHILE the uptrend filter is bullish, AND (per the source's volume-signal
  confirmation guidance) today's volume is above its own `vol_confirm_window`
  -day average (confirms real selling exhaustion, not just illiquid noise).
- Exit: DI rises back to >= `di_exit_threshold` (price has reverted toward
  the MA), OR the uptrend filter flips bearish (source's own warning against
  fading extremes in a downtrend), OR a `max_hold_days` time-stop.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    di_sma_window: int = 20,
    di_entry_threshold: float = -5.0,
    di_exit_threshold: float = 0.0,
    trend_sma_window: int = 50,
    trend_slope_lookback: int = 10,
    vol_confirm_window: int = 20,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]
    n = len(close)

    sma = close.rolling(di_sma_window).mean()
    disparity = 100.0 * (close - sma) / sma

    trend_sma = close.rolling(trend_sma_window).mean()
    trend_bullish = trend_sma > trend_sma.shift(trend_slope_lookback)

    vol_avg = volume.rolling(vol_confirm_window).mean()
    vol_confirm = volume > vol_avg

    entry = (
        (disparity <= di_entry_threshold)
        & trend_bullish.fillna(False)
        & vol_confirm.fillna(False)
    )
    exit_meanrev = disparity >= di_exit_threshold
    exit_trend_flip = ~trend_bullish.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or bool(exit_trend_flip.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
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
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
