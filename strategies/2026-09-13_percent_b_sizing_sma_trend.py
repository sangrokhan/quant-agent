"""Strategy: SMA200 trend-following gate with continuous Bollinger %B
inverse-mean-reversion sizing overlay.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per Wikipedia/Fidelity/GoCharting (browser_exec Google SERP synthesis):
%B (John Bollinger) = (close - lower_band) / (upper_band - lower_band),
where upper/lower bands are the standard N-period SMA +/- k*std bands. %B
equals 0 at the lower band, 1 at the upper band, and can exceed [0, 1]
outside the bands entirely. This repo has 4 prior %B strategies (all
rejected), but all of them used %B as a binary ENTRY/EXIT threshold signal
(e.g. "buy when %B<0.2"). This iteration instead uses %B as a CONTINUOUS
SIZING overlay on the SMA(200) trend gate -- a novel role for this
indicator in this repo, and a fundamentally different type of sizing
signal from every risk-ratio overlay tested elsewhere in this cron trigger
(those are all backward-looking risk/return-ratio measures; %B is a
forward-looking-relative-to-recent-range MEAN-REVERSION positioning
signal). The hypothesis: within an established uptrend (SMA(200) gate),
scale exposure INVERSELY with %B -- i.e. add exposure when price pulls
back toward/below the lower band (buying the dip within the trend) and
reduce exposure when price is stretched toward/above the upper band
(reducing risk after a large run-up), rather than a constant full-size
position whenever the trend gate is satisfied.

Signal logic
------------
- Base directional signal: long-candidate when close > SMA(trend_window).
- Within each day, compute standard Bollinger Bands (bb_window, bb_std) and
  %B = (close - lower_band) / (upper_band - lower_band).
- Exposure while trend_long: base_exposure - pb_sensitivity * (%B - 0.5),
  clipped to [0, leverage_cap] -- i.e. exposure is `base_exposure` when
  %B=0.5 (price at the middle band), rises above base_exposure as %B falls
  toward 0 (dip-buying), and falls below base_exposure as %B rises toward
  1 (de-risking into strength).

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


def _percent_b(close: pd.Series, bb_window: int, bb_std: float) -> pd.Series:
    mid = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()
    upper = mid + bb_std * std
    lower = mid - bb_std * std
    band_width = (upper - lower).replace(0, np.nan)
    pb = (close - lower) / band_width
    return pb


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    bb_window: int = 20,
    bb_std: float = 2.0,
    base_exposure: float = 0.8,
    pb_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    pb = _percent_b(close, bb_window, bb_std)

    raw_exposure = base_exposure - pb_sensitivity * (pb - 0.5)
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
