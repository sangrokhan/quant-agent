"""Strategy: Ehlers Correlation Trend Indicator (CTI) dual-period crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per John Ehlers' "Correlation Trend Indicator" (Stocks & Commodities Magazine,
05/2020), the CTI measures the Pearson/R correlation of the price curve
against an ideal straight-line uptrend over a rolling window of length N,
producing a bounded [-1, +1] trend-quality/direction oscillator (short
windows react fast, long windows are structurally different from a smoothed
short CTI -- Ehlers notes the two "look entirely different"). Per the
ProRealCode transcription of the same article/system
(https://www.prorealcode.com/prorealtime-indicators/ehlers-unique-correlation-trend-indicator-cti/):
"the current CTI system buys when the 5 day CTI crosses over the 10 day CTI
when both values are below -0.5 threshold" (a mean-reversion-style reversal
setup: both timeframes register a downtrend/negative-correlation extreme,
then the faster one turns up first -- an early trend-reversal signal) "and
vice versa for the short entry." We test the long-only version: long when
short-period CTI crosses above long-period CTI while both are below a
negative threshold, exit on the mirror bearish crossover (short CTI crosses
below long CTI while both above +threshold) or a max-hold time-stop.

This is the first CTI/R-correlation-crossover strategy in this repo --
distinct from 2026-09-07-004 (standalone rolling R-squared trend-quality GATE
applied to a separate MA/regression-slope trend signal, no crossover, no
oversold-threshold condition) since here the R-correlation value ITSELF
(dual-period, signed, not squared) is both the entry trigger via a
crossover AND requires an extreme-value co-condition on both periods
simultaneously, which is a fundamentally different construction than a
single-period magnitude threshold gate.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  (0/1 long/flat)
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


def _rolling_cti(close: pd.Series, period: int) -> pd.Series:
    """Rolling Pearson correlation of price vs an ideal downward-indexed
    linear trend line Y = -count (count = 0..period-1, count=0 at the most
    recent bar), per the Ehlers/ProRealCode sum-based formula:
    CTI = (N*SumXY - SumX*SumY) / sqrt((N*SumXX - SumX^2) * (N*SumYY - SumY^2))
    Vectorized via pandas rolling sums (equivalent to, but far faster than,
    a per-window np.corrcoef application) since Y is a fixed sequence
    (-count, count=0..period-1) constant across every window position.
    """
    n = period
    y = -np.arange(n - 1, -1, -1).astype(float)  # matches Y=-count convention
    sum_y = y.sum()
    sum_yy = (y * y).sum()

    x = close.astype(float)
    sum_x = x.rolling(n).sum()
    sum_xx = (x * x).rolling(n).sum()
    # SumXY = sum over window of x_i * y_i where y_i is fixed per-position;
    # compute via a rolling dot product using a weighted rolling sum trick:
    # convolve x with reversed y using rolling.apply is slow, but since y is
    # fixed length n, we can compute it with a rolling window using numpy
    # stride tricks for speed.
    x_vals = x.to_numpy()
    windows = np.lib.stride_tricks.sliding_window_view(x_vals, n) if len(x_vals) >= n else np.empty((0, n))
    sum_xy_vals = windows @ y  # dot product per window
    sum_xy = pd.Series(np.nan, index=x.index)
    if len(x_vals) >= n:
        sum_xy.iloc[n - 1:] = sum_xy_vals

    denom = np.sqrt((n * sum_xx - sum_x * sum_x) * (n * sum_yy - sum_y * sum_y))
    numer = n * sum_xy - sum_x * sum_y
    cti = numer / denom
    cti = cti.where(denom > 0, 0.0)
    return cti


def generate_signals(
    price_df: pd.DataFrame,
    short_period: int = 5,
    long_period: int = 10,
    corr_threshold: float = 0.5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    cti_short = _rolling_cti(close, short_period)
    cti_long = _rolling_cti(close, long_period)

    both_oversold = (cti_short < -corr_threshold) & (cti_long < -corr_threshold)
    both_overbought = (cti_short > corr_threshold) & (cti_long > corr_threshold)

    bullish_cross = (cti_short > cti_long) & (cti_short.shift(1) <= cti_long.shift(1))
    bearish_cross = (cti_short < cti_long) & (cti_short.shift(1) >= cti_long.shift(1))

    entry = bullish_cross & both_oversold.shift(1).fillna(False)
    exit_signal = bearish_cross & both_overbought.shift(1).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
