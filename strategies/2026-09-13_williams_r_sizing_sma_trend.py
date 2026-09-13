"""Strategy: SMA200 trend-following gate with continuous Williams %R
inverse-sizing overlay.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Williams %R (Larry Williams) = (HighestHigh(window) - Close) /
(HighestHigh(window) - LowestLow(window)) * -100, naturally bounded in
[-100, 0]. This repo has 6+ prior Williams %R entries, all using it as a
binary oversold/overbought threshold ENTRY signal (e.g. entry when %R <
-90). This iteration instead uses %R's own naturally bounded scale as a
CONTINUOUS SIZING dial on the SMA(200) trend gate -- the same "reuse a
bounded oscillator as a continuous dial instead of a binary threshold"
pattern that produced two other accepted strategies this cron trigger
(Bollinger %B, 2026-09-13-071; Aroon Oscillator, 2026-09-13-072), applied
here to a THIRD distinct bounded oscillator family for a direct comparison
of which bounded-oscillator construction works best as a sizing dial.
Because %R = -100 at the low of the range and 0 at the high of the range,
exposure = clip(base_exposure - wr_sensitivity * (williams_r / 100.0), 0,
leverage_cap) -- i.e. as %R approaches 0 (price at/near the recent high,
closer to overbought), exposure is reduced from base_exposure; as %R
approaches -100 (price at/near the recent low, a pullback within the
broader uptrend), exposure is increased toward/above base_exposure --
mirroring the %B strategy's "buy the dip within the trend" logic but built
from a High/Low range rather than a std-dev band.
First Williams-%R-as-continuous-sizing strategy in this repo.

Signal logic
------------
- Base directional signal: long-candidate when close > SMA(trend_window).
- Williams %R over `williams_window`.
- Exposure while trend_long: clip(base_exposure + wr_sensitivity *
  (williams_r / 100.0), 0, leverage_cap).

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


def _williams_r(df: pd.DataFrame, window: int) -> pd.Series:
    highest_high = df["high"].rolling(window).max()
    lowest_low = df["low"].rolling(window).min()
    range_ = (highest_high - lowest_low).replace(0, np.nan)
    wr = (highest_high - df["close"]) / range_ * -100.0
    return wr


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    williams_window: int = 14,
    base_exposure: float = 0.8,
    wr_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    williams_r = _williams_r(df, williams_window)

    raw_exposure = base_exposure - wr_sensitivity * (williams_r / 100.0)
    exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap).fillna(0.0)

    position = exposure.where(trend_long.fillna(False), other=0.0)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
