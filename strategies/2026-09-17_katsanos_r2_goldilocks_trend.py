"""Strategy: Katsanos R-squared "Goldilocks zone" trend system
(Markos Katsanos, TASC Oct 2016 "Which Trend Indicator Wins?").

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-137):
Per Markos Katsanos's "Which Trend Indicator Wins?" (TASC Oct 2016;
MetaStock formula disclosed at
https://traders.com/Documentation/FEEDbk_docs/2016/10/TradersTips.html),
a genuinely disclosed R-squared trend system requires the rolling
R-squared (of a linear regression of close vs time, over r2_period bars) to
freshly cross ABOVE a lower threshold (r2_enter, source 0.42) while
remaining BELOW an upper cap (r2_cap, source 0.85 -- "too high" R-squared
means the trend may already be exhausted/overextended) AND have been RISING
over the trailing rising_lookback bars (source: "r2 > Ref(r2,-10)"), AND the
regression's own slope (annualized, source multiplies by 100) must exceed a
minimum positive threshold (slope_min, source 10) confirming trend
DIRECTION (R-squared alone is non-directional -- fits equally well to
uptrends or downtrends). Combined with the source's own price>SMA(50) trend
filter. Exit: source's own rule, close crossing back below the SMA. This is
a specific "Goldilocks zone" trend-quality gate (not just a R2 threshold
gate, and not just a directional slope filter) distinct from this repo's
existing standalone-R2-threshold entry (2026-09-07-004, rejected) and
correlation-crossover entry (2026-09-08-033 CTI, rejected).

Signal logic
------------
- r2 = rolling R-squared of OLS(close ~ time) over r2_period bars.
- slope = rolling OLS slope of close ~ time over r2_period bars, scaled by
  slope_scale (source's "*100" -- kept as a tunable to normalize across
  price levels/asset classes rather than hardcoding 100).
- sma = SMA(close, sma_window).
- r2_cross_enter = r2 crosses above r2_enter (from <= to >).
- zone_ok = r2 < r2_cap AND r2 > r2.shift(rising_lookback) (still rising
  over the lookback).
- Entry (long): r2_cross_enter AND zone_ok AND slope > slope_min AND
  close > sma (all source conditions on the same bar).
- Exit: close crosses back below sma (source's own exit rule), OR
  max_hold_days time-stop (our safety valve).
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _rolling_r2_slope(close: pd.Series, window: int):
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    x_centered = x - x_mean
    ss_xx = (x_centered ** 2).sum()

    def _r2_slope(y: np.ndarray):
        y_mean = y.mean()
        y_centered = y - y_mean
        ss_xy = (x_centered * y_centered).sum()
        ss_yy = (y_centered ** 2).sum()
        if ss_xx <= 0 or ss_yy <= 0:
            return 0.0, 0.0
        slope = ss_xy / ss_xx
        r2 = (ss_xy ** 2) / (ss_xx * ss_yy)
        return r2, slope

    r2_vals = close.rolling(window).apply(lambda w: _r2_slope(w.values)[0], raw=False)
    slope_vals = close.rolling(window).apply(lambda w: _r2_slope(w.values)[1], raw=False)
    return r2_vals, slope_vals


def generate_signals(
    price_df: pd.DataFrame,
    r2_period: int = 18,
    r2_enter: float = 0.42,
    r2_cap: float = 0.85,
    rising_lookback: int = 10,
    slope_min: float = 0.0,
    slope_scale: float = 100.0,
    sma_window: int = 50,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    r2, slope = _rolling_r2_slope(close, r2_period)
    slope_scaled = slope * slope_scale
    sma = close.rolling(sma_window).mean()

    r2_cross_enter = (r2 > r2_enter) & (r2.shift(1) <= r2_enter)
    zone_ok = (r2 < r2_cap) & (r2 > r2.shift(rising_lookback))

    entry = (
        r2_cross_enter.fillna(False)
        & zone_ok.fillna(False)
        & (slope_scaled > slope_min).fillna(False)
        & (close > sma).fillna(False)
    )
    exit_sma_flip = close < sma

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_sma_flip.iloc[i]) or held >= max_hold_days:
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
