"""Strategy: SMA(trend_window) directional gate with continuous Polarized
Fractal Efficiency (PFE) sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-14-102):
Polarized Fractal Efficiency (Hans Hannula, 1994, Technical Analysis of
Stocks & Commodities; formula per direct Investopedia page read via
browser_exec):
    P_i = 100 * sqrt((Price_i - Price_{i-N})^2 + N^2)
              / sum_{j=0}^{N-2} sqrt((Price_{i-j} - Price_{i-j-1})^2 + 1)
    P_i = -P_i  if Close_i < Close_{i-1}
    PFE_i = EMA(P_i, M)
This measures the straight-line ("as the crow flies") Euclidean distance
price traveled over N bars against the actual cumulative bar-to-bar path
length -- a fractal-efficiency ratio -- then signs it by the latest bar's
direction and EMA-smooths it. Bounded roughly [-100, 100] by construction
(a ratio of a straight-line distance to a path length that is at least as
long, capped near 100 in the fully-efwith limit).

This repo has one prior PFE entry (2026-09-05-014), a binary
threshold-crossover (+50/-50 zones) ENTRY trigger, decisively rejected. This
iteration instead uses PFE as a CONTINUOUS SIZING dial within an
SMA(trend_window) uptrend gate -- same reframing pattern that rescued
VHF/ADX/CHOP (fellow trend-efficiency/trend-strength measures) earlier this
cron trigger, testing whether PFE's fractal-geometry construction (distinct
from VHF's simpler net-range/path-length ratio) offers similar or
complementary signal once freed from a brittle threshold-crossing rule.

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


def _pfe(close: pd.Series, period: int = 10, smoothing_period: int = 5) -> pd.Series:
    """Polarized Fractal Efficiency, bounded ~[-100, 100]."""
    n = period
    straight_line = np.sqrt((close - close.shift(n)) ** 2 + n ** 2)

    step_dist = np.sqrt((close - close.shift(1)) ** 2 + 1.0)
    path_length = step_dist.rolling(n - 1).sum()

    p = 100.0 * straight_line / path_length.replace(0, np.nan)

    down_day = close < close.shift(1)
    p = p.where(~down_day.fillna(False), -p)

    pfe = p.ewm(span=smoothing_period, adjust=False).mean()
    return pfe.clip(lower=-100.0, upper=100.0)


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
    pfe_period: int = 10,
    pfe_smoothing: int = 5,
    base_exposure: float = 0.5,
    pfe_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.30,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    pfe = _pfe(close, period=pfe_period, smoothing_period=pfe_smoothing)
    pfe_norm = pfe / 100.0  # rescale to roughly [-1, 1]

    raw_exposure = base_exposure + pfe_sensitivity * pfe_norm
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    pfe_period: int = 10,
    pfe_smoothing: int = 5,
    base_exposure: float = 0.5,
    pfe_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.30,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        pfe_period=pfe_period,
        pfe_smoothing=pfe_smoothing,
        base_exposure=base_exposure,
        pfe_sensitivity=pfe_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
