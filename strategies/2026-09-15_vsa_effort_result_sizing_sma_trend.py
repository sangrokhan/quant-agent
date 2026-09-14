"""Strategy: SMA(trend_window) directional gate with continuous VSA
"Effort vs Result" (volume-per-spread efficiency) sizing overlay +
deadband, leverage-cap-aware.

Hypothesis (knowledge_base id 2026-09-15-038, this cron trigger):
Volume Spread Analysis (VSA, Tom Williams, built on Wyckoff's "effort vs
result" concept), per Google's AI-overview summary and multiple corroborating
sources (LuxAlgo, ATAS, VT Markets, all visited this iteration):
  No-Demand bar: narrow-spread UP bar on unusually LOW volume (weak buying
    effort produced little result -- bearish warning in an uptrend)
  No-Supply bar: narrow-spread DOWN bar on unusually LOW volume (weak
    selling effort produced little result -- bullish sign in a downtrend)

This repo's prior VSA entry (2026-09-06-130) implemented this as a
discrete narrow-spread-bar-pattern rule (bar-by-bar classification +
confirmation-bar entry) and was rejected decisively (3/144 grid cells
passed, consistent with the signal-sparsity failure mode this cron
trigger's log shows repeatedly for discrete bar/threshold rules). This
iteration reuses the identical underlying "effort vs result" concept --
volume relative to price spread, i.e. how much price movement a given
amount of volume "effort" produced -- but as a CONTINUOUS sizing dial
rather than a discrete bar classification, per this trigger's established
rescue pattern (successfully applied to WaveTrend CI, McGinley Dynamic,
DSS Bressert, Gann HiLo, and others this same trigger).

Construction: `effort_result[t] = volume[t] / (high[t]-low[t])` (volume
per unit of price spread -- Wyckoff's "effort"-to-"result" ratio, high when
a lot of volume moves price only a little, i.e. absorption/no-result;
low when a little volume moves price a lot, i.e. high-efficiency effort).
This is rolling z-scored and tanh-squashed into [-1,+1], with the SIGN
INVERTED so that low effort-per-result (efficient, high-conviction moves)
scales exposure UP and high effort-per-result (absorption/no-result,
consistent with distribution/weak participation) scales exposure DOWN,
inside an SMA(trend_window) uptrend gate for direction, with a deadband to
cut turnover.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
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


def _effort_vs_result(df: pd.DataFrame) -> pd.Series:
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=df.index)

    spread = (high - low).replace(0.0, np.nan)
    effort_per_result = volume / spread
    return effort_per_result


def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
    raw = raw_exposure.fillna(0.0).to_numpy()
    held = np.zeros_like(raw)
    current = 0.0
    for i, r in enumerate(raw):
        if abs(r - current) > deadband:
            current = r
        held[i] = current
    return pd.Series(held, index=raw_exposure.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    smooth_window: int = 5,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    volume/spread ("effort per unit of result") is smoothed over
    `smooth_window` bars, rolling z-scored over `zscore_window`, and
    tanh-squashed to [-1,+1] with the SIGN INVERTED (low effort-per-result
    = efficient/high-conviction move = scale exposure UP) before use as a
    sizing dial, gated by an SMA(trend_window) uptrend filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    effort = _effort_vs_result(df)
    effort_smoothed = effort.rolling(smooth_window).mean()

    roll_mean = effort_smoothed.rolling(zscore_window).mean()
    roll_std = effort_smoothed.rolling(zscore_window).std()
    zscore = (effort_smoothed - roll_mean) / roll_std.replace(0.0, np.nan)
    # Invert: low effort-per-result (efficient move) -> positive dial.
    dial = -np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    smooth_window: int = 5,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        smooth_window=smooth_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
