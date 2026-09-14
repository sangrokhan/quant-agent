"""Strategy: SMA(trend_window) directional gate with continuous Double
Smoothed Stochastic (DSS, William Blau) sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
DSS (Double Smoothed Stochastic, William Blau) applies two chained EMA
smoothings to the raw Stochastic %K numerator/denominator components
BEFORE computing the ratio (rather than smoothing the ratio itself, as %D
does), producing a much smoother oscillator than the raw Stochastic, still
naturally bounded [0,100] by construction:

    HH = rolling max(high, stoch_period), LL = rolling min(low, stoch_period)
    CL = close - LL,  HL = HH - LL
    CL2 = EMA(CL, period2),  HL2 = EMA(HL, period2)
    CL1 = EMA(CL2, period1), HL1 = EMA(HL2, period1)
    DSS = 100 * CL1 / HL1

Per http://www2.wealth-lab.com/WL5Wiki/DSS.ashx (Wealth-Lab DSS wiki page,
re-confirmed this iteration via browser_exec Google SERP fallback after
web_search's DDGS backend surfaced generic Volume-Weighted-MACD/OBV content
for the initial query attempted; this repo's own prior 2026-09-10-081
entry already documented and implemented this formula from the same
source).

This repo has 1 prior DSS entry (2026-09-10-081, oversold-turn-up/
turn-down entry with NO trend/regime filter -- REJECTED: QQQ marginally
cleared Sharpe but failed MDD decisively at 29.6% vs 25% cap, falling-knife
drawdowns from lacking a trend filter; SPY failed outright; crypto rejected
0/36). This iteration directly addresses that rejection mode by (a) adding
an SMA(trend_window) uptrend gate to avoid falling-knife entries, and (b)
reframing DSS as a CONTINUOUS SIZING dial (rescaled [0,100] -> [-1,+1] via
(DSS-50)/50) rather than a discrete turn-up/turn-down entry/exit rule --
following this cron trigger's now-repeatedly-validated sizing-dial pattern.

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


def _dss(df: pd.DataFrame, stoch_period: int, period1: int, period2: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    hh = high.rolling(stoch_period).max()
    ll = low.rolling(stoch_period).min()
    cl = close - ll
    hl = (hh - ll).replace(0.0, np.nan)

    cl2 = cl.ewm(span=period2, adjust=False).mean()
    hl2 = hl.ewm(span=period2, adjust=False).mean()
    cl1 = cl2.ewm(span=period1, adjust=False).mean()
    hl1 = hl2.ewm(span=period1, adjust=False).mean()

    dss = 100.0 * cl1 / hl1
    return dss.fillna(50.0).clip(lower=0.0, upper=100.0)


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
    stoch_period: int = 13,
    period1: int = 8,
    period2: int = 3,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    DSS is bounded [0,100] by construction; rescaled to [-1,+1] via
    (DSS-50)/50, then used directly as a sizing dial within the
    SMA(trend_window) uptrend gate -- addressing 2026-09-10-081's
    falling-knife MDD failure by never taking exposure outside an uptrend.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    dss = _dss(df, stoch_period, period1, period2)
    dss_centered = (dss - 50.0) / 50.0  # rescale [0,100] -> [-1,+1]

    raw_exposure = base_exposure + sensitivity * dss_centered
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    stoch_period: int = 13,
    period1: int = 8,
    period2: int = 3,
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
        stoch_period=stoch_period,
        period1=period1,
        period2=period2,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
