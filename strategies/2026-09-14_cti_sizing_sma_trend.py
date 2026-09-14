"""Strategy: SMA(trend_window) directional gate with continuous Ehlers
Correlation Trend Indicator (CTI) sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
Ehlers Correlation Trend Indicator (CTI, Stocks & Commodities 05/2020):
rolling Pearson/Spearman correlation of price against an "ideal" straight
uptrend ramp of a given slope, over a lookback of n bars -- naturally
bounded in [-1, +1] by construction (a correlation coefficient), no
z-scoring or min-max normalization required, unlike most other indicators
tested in this cron trigger. Per TTR R package canonical docs
(https://rdrr.io/cran/TTR/man/CTI.html, visited this iteration via
browser_exec after web_extract's DDGS backend couldn't fetch page content --
search-only backend limitation, not a page-specific failure): "Positive/
negative CTI values signal positive/negative correlation with the desired
trend line slope. A simple strategy could be long when the CTI is positive
and, short when it is negative" (author's own stated rule).

This repo's prior CTI entry (2026-09-08-033) used CTI in a dual-period
CROSSOVER system (short-period CTI crossing long-period CTI at oversold
extremes) and was REJECTED for decisive parameter-sensitivity failure
(relative_std 2.60, grid pass_fraction only 6/144). This iteration
addresses that failure directly: instead of a crossover/threshold rule
that depends on brittle extreme cutoffs, use the single-period CTI value
DIRECTLY as a continuous sizing dial -- since it's already bounded [-1,1],
map it straight to [0, leverage_cap] exposure within the existing SMA
trend gate, following this cron trigger's validated continuous-sizing-dial
pattern (many prior indicator families) rather than the crossover
formulation that failed for this specific indicator.

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


def _cti(close: pd.Series, period: int = 20, slope: float = 1.0) -> pd.Series:
    """Ehlers CTI: rolling Pearson correlation of price vs an ideal linear
    trend ramp (0, slope, 2*slope, ..., (period-1)*slope) over `period` bars.

    Bounded in [-1, +1] by construction (a correlation coefficient).
    """
    ramp = np.arange(period, dtype=float) * slope

    def _corr(window: np.ndarray) -> float:
        if np.std(window) == 0:
            return 0.0
        return float(np.corrcoef(window, ramp)[0, 1])

    return close.rolling(period).apply(_corr, raw=True)


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
    cti_period: int = 20,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    CTI is already bounded in [-1, +1] by construction -- no normalization
    needed. Exposure = base_exposure + sensitivity * CTI, clipped to
    [0, leverage_cap], gated to zero outside the SMA(trend_window) uptrend.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    cti = _cti(close, cti_period, slope=1.0)

    raw_exposure = base_exposure + sensitivity * cti
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    cti_period: int = 20,
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
        cti_period=cti_period,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
