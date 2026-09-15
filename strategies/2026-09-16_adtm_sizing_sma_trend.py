"""Strategy: SMA(trend_window) directional gate with continuous ADTM
(Dynamic Buying/Selling Power indicator, Chinese-market sentiment
oscillator) sizing overlay + deadband, leverage-cap-aware for crypto from
the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
ADTM (Dynamic Buying and Selling Power Indicator) compares intraday
buying momentum vs selling momentum, anchored on the OPENING price
relative to the prior day's open (structurally distinct from AR/BR/CR,
this cron trigger's own prior 3 entries this iteration set, which anchor
on open/close/median-price respectively vs the CURRENT day's high/low --
ADTM instead compares TODAY's high/low extension against TODAY's open
relative to YESTERDAY's open). Formula confirmed via two independent
sources this iteration (Google SERP synthesis, browser_exec):
Luo/Li/Liu 2021 AIMS Press "Does investor sentiment affect stock pricing?"
paper (https://www.aimspress.com/article/doi/10.3934/NAR.2021006) and
10jqka.com.cn's formula-platform page (poi.10jqka.com.cn), both
corroborating:

    DTM(t) = 0                                      if Open(t) <= Open(t-1)
           = max(High(t)-Open(t), Open(t)-Open(t-1)) otherwise
    DBM(t) = 0                                      if Open(t) >= Open(t-1)
           = max(Open(t)-Low(t), Open(t-1)-Open(t))  otherwise
    STM(N) = SUM(DTM, N)
    SBM(N) = SUM(DBM, N)
    ADTM   = (STM-SBM)/STM   if STM > SBM
           = (SBM-STM)/SBM   if STM < SBM
           = 0               if STM == SBM

ADTM is naturally bounded ~[-1,+1] by construction (no z-score needed,
similar to CTI/PSO in this repo). Source's own stated conventional
levels: N=23 summation period, M=8 signal-line MA period, -0.5/+0.5
oversold/overbought thresholds. First ADTM strategy in this repo -- no
prior DTM/DBM/ADTM entries found in Stage-1 keyword search.

This iteration reframes ADTM as a CONTINUOUS SIZING dial (used directly,
already bounded [-1,1]) inside an SMA(trend_window) uptrend gate with a
deadband to cut turnover, following this repo's established
continuous-sizing-dial pattern, leverage-cap-aware for crypto from the
start.

Source: https://www.aimspress.com/article/doi/10.3934/NAR.2021006 (exact
DTM/DBM/STM/SBM/ADTM formula) and http://poi.10jqka.com.cn (corroborating
formula-platform snippet), both surfaced via Google SERP synthesis this
iteration (browser_exec; the TradingView Pine Script port and
AIMS-Press-hosted PDF full text were inaccessible/paywalled-by-JS, but
the Google SERP snippet itself quoted the exact formula text verbatim
from both sources, corroborating each other).

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


def _compute_adtm(df: pd.DataFrame, window: int) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    open_ = df["open"].astype(float) if "open" in df.columns else df["close"].shift(1).astype(float)
    prev_open = open_.shift(1)

    dtm = np.where(
        open_ <= prev_open,
        0.0,
        np.maximum(high - open_, open_ - prev_open),
    )
    dbm = np.where(
        open_ >= prev_open,
        0.0,
        np.maximum(open_ - low, prev_open - open_),
    )
    dtm = pd.Series(dtm, index=df.index)
    dbm = pd.Series(dbm, index=df.index)

    stm = dtm.rolling(window).sum()
    sbm = dbm.rolling(window).sum()

    adtm = pd.Series(0.0, index=df.index)
    gt = stm > sbm
    lt = stm < sbm
    adtm[gt] = (stm[gt] - sbm[gt]) / stm[gt].replace(0.0, np.nan)
    adtm[lt] = (sbm[lt] - stm[lt]) / sbm[lt].replace(0.0, np.nan)
    # STM==SBM (or both zero) stays 0 by initialization.
    return adtm.fillna(0.0)


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
    adtm_window: int = 23,
    base_exposure: float = 0.4,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    ADTM (already naturally bounded [-1,+1]) is used directly as a sizing
    dial, gated by an SMA(trend_window) uptrend filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    dial = _compute_adtm(df, adtm_window)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    adtm_window: int = 23,
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
        adtm_window=adtm_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
