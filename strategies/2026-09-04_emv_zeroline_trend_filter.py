"""Strategy: Ease of Movement (EMV, Richard Arms) zero-line cross, gated by
an SMA long-term trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-115):
EMV is a volume-based oscillator (Distance Moved / Box Ratio, smoothed by an
n-period SMA -- default 14) that measures how "easily" price moves per unit
of volume. Source (quantifiedstrategies.com/ease-of-movement/, Google AI
overview) explicitly states the indicator is rarely reliable standalone and
recommends combining it with a moving-average trend filter: the MA
identifies the trend, EMV confirms conviction behind the move. Long entry
when EMV(emv_period) crosses above zero (bullish, "easy" upward movement)
while price is in a long-term uptrend (close > SMA(trend_window)); exit when
EMV crosses back below zero, or after a max_hold_days time-stop.

Signal logic
------------
- Distance Moved = midpoint(t) - midpoint(t-1), midpoint = (H+L)/2.
- Box Ratio = (Volume/scale) / (H-L), scale auto-derived from average
  dollar-volume-ish level so raw EMV isn't astronomically large/small.
- 1-period EMV = Distance Moved / Box Ratio.
- EMV(emv_period) = SMA(emv_period) of 1-period EMV.
- Trend filter: close > SMA(trend_window).
- Entry (long): EMV crosses from <=0 to >0 AND close > SMA(trend_window).
- Exit: EMV crosses back to <=0, OR max_hold_days time-stop reached.
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept params as keyword args.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _compute_emv(df: pd.DataFrame, emv_period: int) -> pd.Series:
    import numpy as np

    high = df["high"].astype(float)
    low = df["low"].astype(float)
    volume = df["volume"].astype(float).replace(0.0, np.nan).ffill().fillna(1.0)

    midpoint = (high + low) / 2.0
    distance_moved = midpoint.diff()

    hl_range = (high - low).replace(0.0, np.nan)
    # Auto-scale volume so box_ratio isn't degenerate across wildly
    # different symbol volume magnitudes (equities vs. crypto units).
    scale = volume.rolling(252, min_periods=20).median().bfill().ffill()
    scale = scale.replace(0.0, 1.0).fillna(1.0)

    box_ratio = (volume / scale) / hl_range
    one_period_emv = (distance_moved / box_ratio).astype(float)
    one_period_emv = one_period_emv.replace([np.inf, -np.inf], np.nan)

    emv = one_period_emv.rolling(emv_period, min_periods=emv_period).mean()
    return emv


def generate_signals(
    price_df: pd.DataFrame,
    emv_period: int = 14,
    trend_window: int = 200,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    emv = _compute_emv(df, emv_period)
    sma_trend = close.rolling(trend_window, min_periods=trend_window).mean()
    uptrend = close > sma_trend

    emv_prev = emv.shift(1)
    cross_up = (emv_prev <= 0) & (emv > 0)
    cross_down = (emv_prev > 0) & (emv <= 0)

    entry = cross_up.fillna(False) & uptrend.fillna(False)
    exit_cross = cross_down.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or held >= max_hold_days:
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
