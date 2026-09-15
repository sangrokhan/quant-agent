"""Strategy: SMA(trend_window) directional gate with continuous CR
("energy index" / intermediate willingness index, median-price-based
sibling of BRAR) sizing overlay + deadband, leverage-cap-aware for crypto
from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
CR is a Chinese-market "energy index", structurally similar to AR/BR
(this cron trigger's own 2026-09-16-099 BRAR entry) but uses the PRIOR
DAY's median price (mid = (PrevHigh+PrevLow)/2) as its reference rather
than the open (AR) or prior close (BR). Per
https://www.futuhk.com/en/support/topic1_167 (visited this iteration via
browser_exec):

    prev_mid(t) = (High(t-1) + Low(t-1)) / 2
    strong_sum(N) = SUM(max(0, High(t) - prev_mid(t)), N)
    weak_sum(N)   = SUM(max(0, prev_mid(t) - Low(t)), N)
    CR(N) = 100 * strong_sum(N) / weak_sum(N)

Source states CR's own personality "is between AR and BR, closer to BR"
and is meant to complement BRAR's blind spots ("assist BRAR's
shortcomings") -- explicitly framed by the source as a companion/distinct
indicator, not a redundant duplicate, justifying testing it as a separate
strategy right after this cron trigger's BRAR entry. Midline is 100
(balanced); source's own numeric levels: CR<40 = likely bottom formation,
CR>300-400 = likely reversal risk.

This iteration reframes CR as a CONTINUOUS SIZING dial (rolling z-score
normalized + tanh-squashed to [-1,1]) rather than a threshold trigger,
inside an SMA(trend_window) uptrend gate with a deadband to cut turnover,
following this repo's established continuous-sizing-dial pattern,
leverage-cap-aware for crypto from the start.

Source: https://www.futuhk.com/en/support/topic1_167 (exact CR formula),
visited via browser_exec this iteration (following up directly from the
BRAR source page's own cross-reference to CR).

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


def _compute_cr(df: pd.DataFrame, window: int) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)

    prev_mid = ((high + low) / 2.0).shift(1)

    strong = (high - prev_mid).clip(lower=0.0).rolling(window).sum()
    weak = (prev_mid - low).clip(lower=0.0).rolling(window).sum().replace(0.0, np.nan)

    cr = 100.0 * strong / weak
    return cr


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
    cr_window: int = 26,
    zscore_window: int = 60,
    base_exposure: float = 0.4,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    CR is rolling z-score normalized then tanh-squashed to bounded
    [-1,1], used as a sizing dial gated by an SMA(trend_window) uptrend
    filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    cr = _compute_cr(df, cr_window)
    roll_mean = cr.rolling(zscore_window, min_periods=zscore_window).mean()
    roll_std = cr.rolling(zscore_window, min_periods=zscore_window).std().replace(0.0, np.nan)
    z = ((cr - roll_mean) / roll_std).fillna(0.0)
    dial = np.tanh(z)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    cr_window: int = 26,
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
        cr_window=cr_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
