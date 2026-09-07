"""Strategy: Volatility Quality Index (VQI, Thomas Stridsman) streak
confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-028):
Per Thomas Stridsman's Volatility Quality Index construction (formula
per id.tradingview.com's disclosed transcription of a VQI-family
indicator; trading rule per LazyBear's VQI_LB TradingView page and Google's
AI-overview synthesis of multiple VQI sources):

    Bar Range      = True Range (TR)
    Weighted Vol.  = Bar Range * sign(Close - Open)   (+1 bullish, -1
                     bearish, 0 doji)
    VQI Raw        = EMA(Weighted Volatility, vqi_length)
    VQI Smoothed   = EMA(VQI Raw, smoothing_length)

Stridsman's own stated trading rule (LazyBear): "buy when VQI has
increased in the previous 10 bars... sell when it has decreased in the
previous 10 bars" -- i.e. a STREAK confirmation rather than a level
threshold or single-bar crossover, intended to separate "good" (efficient,
directionally-productive) volatility from "bad" (choppy, whipsaw) volatility.
This is a genuinely new construction in this repo: distinct from all
ATR/True-Range-based strategies already tested (ATR expansion breakout,
Chandelier Exit, SuperTrend, STARC bands, Keltner Channels) because VQI
signs the True Range by same-bar candle direction and smooths that SIGNED
series with a double EMA, then requires a persistent N-bar rising/falling
STREAK of the resulting smoothed line -- not a threshold level, band
touch, or single crossover.

Signal logic
------------
- Compute VQI Smoothed per the formula above.
- Long entry: VQI Smoothed has been monotonically increasing for the last
  `streak_bars` consecutive bars (Stridsman's own disclosed "increased in
  previous 10 bars" rule).
- Exit: VQI Smoothed has been monotonically DECREASING for the last
  `streak_bars` consecutive bars (source's mirror sell rule), or a
  `max_hold_days` time-stop (added for robustness, not in source).
- Flat otherwise; long-only, matching repo convention.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _true_range(df: pd.DataFrame) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _vqi_smoothed(df: pd.DataFrame, vqi_length: int, smoothing_length: int) -> pd.Series:
    tr = _true_range(df)
    direction = np.sign(df["close"] - df["open"])
    weighted_vol = tr * direction
    vqi_raw = weighted_vol.ewm(span=vqi_length, min_periods=vqi_length, adjust=False).mean()
    vqi_smoothed = vqi_raw.ewm(span=smoothing_length, min_periods=smoothing_length, adjust=False).mean()
    return vqi_smoothed


def generate_signals(
    price_df: pd.DataFrame,
    vqi_length: int = 14,
    smoothing_length: int = 5,
    streak_bars: int = 10,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    vqi = _vqi_smoothed(df, vqi_length, smoothing_length)

    diff = vqi.diff()
    rising = diff > 0
    falling = diff < 0

    # Rolling streak: True if the last `streak_bars` diffs are ALL rising
    # (or all falling), matching Stridsman's "increased/decreased in the
    # previous N bars" rule.
    rising_streak = rising.rolling(streak_bars).sum() == streak_bars
    falling_streak = falling.rolling(streak_bars).sum() == streak_bars

    valid = vqi.notna() & rising_streak.notna() & falling_streak.notna()

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(len(df)):
        if not valid.iloc[i]:
            position.iloc[i] = 0
            continue
        if in_position:
            held = i - entry_idx
            if bool(falling_streak.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(rising_streak.iloc[i]):
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
