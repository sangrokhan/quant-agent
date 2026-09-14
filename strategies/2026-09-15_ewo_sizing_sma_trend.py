"""Strategy: SMA(trend_window) directional gate with continuous Elliott Wave
Oscillator (EWO, 5/35-period SMA difference) sizing overlay + deadband,
leverage-cap-aware.

Hypothesis (knowledge_base id 2026-09-15-034, this cron trigger):
Elliott Wave Oscillator, per https://www.daytrading.com/elliott-wave-oscillator
and Google's AI-overview summary (visited this iteration):
  EWO = SMA(close, fast_len) - SMA(close, slow_len)   (defaults fast=5, slow=35)

This is a genuinely new indicator family for this repo (0 prior
strategies/log entries reference "Elliott Wave Oscillator" or "EWO").
DayTrading.com's own disclosed trade criteria: long when EWO is positive by
a threshold AND increasing AND a slower (50-period) SMA is positively
sloped; the source explicitly warns that raw EWO crossovers alone produce
"a ton of signals" and need strict filtering/magnitude thresholds to avoid
false positives in consolidating markets.

Rather than implementing the source's discrete threshold+slope+trend-filter
AND-rule directly (this repo's log shows discrete oscillator threshold
rules consistently underperform continuous z-score/tanh dials for this
family of indicator -- see WaveTrend CI, McGinley Dynamic distance, DSS
Bressert, Gann HiLo distance, all this cron trigger), this implementation
normalizes EWO by price (EWO/close, since raw SMA-difference is not
naturally bounded/comparable across price levels or assets) then rolling
z-scores and tanh-squashes it into [-1,+1] as an exposure multiplier inside
an SMA(trend_window) uptrend gate, with a deadband to cut turnover -- the
cron trigger's established continuous-sizing-dial pattern, directly
addressing the source's own "needs strict filtering" caveat by making the
magnitude threshold implicit (further from zero-crossing = closer to full
z-score saturation = larger sizing swing) rather than a hard binary
+X/-X cutoff.

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


def _ewo_pct(close: pd.Series, fast_len: int, slow_len: int) -> pd.Series:
    fast = close.rolling(fast_len).mean()
    slow = close.rolling(slow_len).mean()
    ewo = fast - slow
    return ewo / close.replace(0.0, np.nan)


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
    fast_len: int = 5,
    slow_len: int = 35,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    EWO (as a fraction of price, so it's comparable across symbols/price
    levels) is rolling z-scored over `zscore_window` and tanh-squashed to
    [-1,+1] before use as a sizing dial, gated by an SMA(trend_window)
    uptrend filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    ewo_pct = _ewo_pct(close, fast_len, slow_len)

    roll_mean = ewo_pct.rolling(zscore_window).mean()
    roll_std = ewo_pct.rolling(zscore_window).std()
    zscore = (ewo_pct - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    fast_len: int = 5,
    slow_len: int = 35,
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
        fast_len=fast_len,
        slow_len=slow_len,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
