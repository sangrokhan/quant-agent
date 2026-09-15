"""Strategy: SMA(trend_window) directional gate with continuous Ease-of-
Movement (EMV, Richard W. Arms Jr.) sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Ease of Movement (EMV) is a volume-based oscillator (this repo has 1 prior
entry, 2026-09-04-115, a binary zero-line-cross + SMA(200) trend filter
trigger, accepted QQQ+SPY, rejected crypto). Formula (per
chartschool.stockcharts.com / quantifiedstrategies.com, both already on
file in this repo from the prior EMV entry, re-used unchanged this
sub-iteration since the exact formula is not in question -- only the
sizing reframing is new):

    Distance Moved(t) = midpoint(t) - midpoint(t-1), midpoint=(H+L)/2
    Box Ratio(t)       = (Volume(t)/scale) / (High(t)-Low(t))
    1-period EMV(t)     = Distance Moved(t) / Box Ratio(t)
    EMV(emv_period)     = SMA(emv_period) of 1-period EMV

This iteration reframes EMV as a CONTINUOUS SIZING dial (rolling z-score
normalized + tanh-squashed to bounded [-1,1]) rather than a binary
zero-line-cross entry trigger -- first EMV continuous-sizing variant in
this repo, following the established continuous-sizing-dial pattern used
for TRIX/DPO/Qstick/Chaikin Oscillator/etc. Gated by an SMA(trend_window)
uptrend filter with a deadband to cut turnover, leverage-cap-aware for
crypto from the start (base_exposure/sensitivity/leverage_cap all
parameterized rather than hardcoded, per the repo's crypto MDD-rejection
lessons learned from binary-trigger EMV and many other prior entries).

Source: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/ease-of-movement-emv
and https://www.quantifiedstrategies.com/ease-of-movement/ (both already
documented in this repo's knowledge base from the prior binary EMV entry,
2026-09-04-115 -- formula not re-fetched this sub-iteration, reused as-is
per novelty-check dedupe rule since only the sizing reframe is new).

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


def _compute_emv(df: pd.DataFrame, emv_period: int) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    volume = df["volume"].astype(float).replace(0.0, np.nan).ffill().fillna(1.0)

    midpoint = (high + low) / 2.0
    distance_moved = midpoint.diff()

    hl_range = (high - low).replace(0.0, np.nan)
    scale = volume.rolling(252, min_periods=20).median().bfill().ffill()
    scale = scale.replace(0.0, 1.0).fillna(1.0)
    box_ratio = (volume / scale) / hl_range

    emv_1p = distance_moved / box_ratio.replace(0.0, np.nan)
    emv = emv_1p.rolling(emv_period, min_periods=emv_period).mean()
    return emv


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
    emv_period: int = 14,
    zscore_window: int = 60,
    base_exposure: float = 0.4,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    EMV is rolling z-score normalized then tanh-squashed to bounded
    [-1,1], used as a sizing dial gated by an SMA(trend_window) uptrend
    filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    emv = _compute_emv(df, emv_period)
    roll_mean = emv.rolling(zscore_window, min_periods=zscore_window).mean()
    roll_std = emv.rolling(zscore_window, min_periods=zscore_window).std().replace(0.0, np.nan)
    z = ((emv - roll_mean) / roll_std).fillna(0.0)
    dial = np.tanh(z)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    emv_period: int = 14,
    zscore_window: int = 60,
    base_exposure: float = 0.4,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        emv_period=emv_period,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
