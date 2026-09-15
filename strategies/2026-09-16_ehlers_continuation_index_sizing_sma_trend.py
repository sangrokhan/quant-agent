"""Strategy: Ehlers Continuation Index (TASC Sep 2025) used directly as a
CONTINUOUS SIZING dial within an SMA(trend_window) uptrend gate,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per PineCodersTASC's exact disclosed Pine v6 source
(https://www.tradingview.com/script/5ZrOut79-TASC-2025-09-The-Continuation-Index/,
visited this iteration via browser_exec fallback -- web_search failed/no
useful direct results this iteration, browser_exec Google SERP found the
exact source): the Continuation Index (CI) is the Inverse Fisher Transform
of the normalized difference between two smoothers applied to price:

    us  = UltimateSmoother(close, length // 2)     (Ehlers' low-lag 2-pole
                                                      highpass-subtracted
                                                      smoother, TASC Apr 2024)
    lg  = N-order Laguerre filter (order=8, gamma=0.8) built recursively on
          top of UltimateSmoother(close, length)
    ref = 2 * (us - lg) / SMA(|us - lg|, length)
    CI  = (exp(2*ref) - 1) / (exp(2*ref) + 1)        (Inverse Fisher Transform,
                                                        naturally bounded [-1,+1])

Source's own disclosed usage rule: CI near +1 signals long-side trend
continuation, CI near -1 signals short-side/downtrend, intermediate
readings suggest "buy the dip"/"sell the pop" fluctuation opportunities
within an existing trend. Ehlers' own observation: in a trend, price tends
to stay to one side of a Laguerre filter, so the smoother-vs-filter spread
(normalized and Fisher-transformed) becomes a clean trend-strength
indicator. Because CI is already bounded [-1,+1] by construction (like
several other successfully-tested continuous-sizing indicators in this
repo -- ADTM, BMP, PSO), it is used DIRECTLY as a sizing multiplier here
(no z-score/tanh needed), inside an SMA(trend_window) uptrend gate (long
only, per this repo's long-only convention) with a deadband to cut
turnover, leverage-cap-aware for crypto from the start.

First Ehlers Continuation Index strategy in this repo -- distinct from this
same cron trigger's Reversion Index entries (a mean-reversion oscillator
Ehlers explicitly designed for RANGING markets) and from this repo's other
Laguerre-filter entry (Laguerre RSI, a completely different construction --
Laguerre-filtered RSI values, not an Inverse-Fisher-Transformed
smoother-vs-filter spread).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _ultimate_smoother(src: pd.Series, period: int) -> pd.Series:
    """Ehlers' UltimateSmoother (TASC Apr 2024): allpass minus highpass."""
    period = max(int(period), 1)
    a1 = math.exp(-1.414 * math.pi / period)
    c2 = 2.0 * a1 * math.cos(1.414 * math.pi / period)
    c3 = -a1 * a1
    c1 = (1.0 + c2 - c3) / 4.0

    vals = src.ffill().fillna(0.0).to_numpy()
    n = len(vals)
    us = np.zeros(n)
    for i in range(n):
        if i < 4:
            us[i] = vals[i]
        else:
            us[i] = (
                (1.0 - c1) * vals[i]
                + (2.0 * c1 - c2) * vals[i - 1]
                - (c1 + c3) * vals[i - 2]
                + c2 * us[i - 1]
                + c3 * us[i - 2]
            )
    return pd.Series(us, index=src.index)


def _laguerre_filter(src: pd.Series, gamma: float, order: int, length: int) -> pd.Series:
    """N-order Laguerre filter built recursively on top of UltimateSmoother."""
    us = _ultimate_smoother(src, length).to_numpy()
    n = len(us)
    order = max(int(order), 1)
    # lg[i][0] = current value of stage i, lg[i][1] = previous value of stage i
    lg_cur = np.zeros(order)
    lg_prev = np.zeros(order)
    fir_series = np.zeros(n)
    for t in range(n):
        new_lg = np.zeros(order)
        new_lg[0] = us[t]
        for i in range(1, order):
            new_lg[i] = gamma * (new_lg[i - 1] - lg_prev[i - 1]) + lg_prev[i - 1]
        lg_prev = lg_cur.copy()
        lg_cur = new_lg
        fir_series[t] = new_lg.sum() / order
    return pd.Series(fir_series, index=src.index)


def _continuation_index(
    close: pd.Series, gamma: float, order: int, length: int
) -> pd.Series:
    us = _ultimate_smoother(close, max(length // 2, 1))
    lg = _laguerre_filter(close, gamma, order, length)
    diff = us - lg
    denom = diff.abs().rolling(length).mean()
    ref = (2.0 * diff / denom.replace(0.0, np.nan)).fillna(0.0)
    ref = ref.clip(lower=-15.0, upper=15.0)  # avoid exp overflow
    ci = (np.exp(2.0 * ref) - 1.0) / (np.exp(2.0 * ref) + 1.0)
    return ci


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
    ci_length: int = 40,
    ci_gamma: float = 0.8,
    ci_order: int = 8,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    CI (already bounded [-1,+1] by construction) is used directly as the
    sizing dial -- no z-score/tanh transform needed.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    ci = _continuation_index(close, ci_gamma, ci_order, ci_length)

    raw_exposure = base_exposure + sensitivity * ci
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    ci_length: int = 40,
    ci_gamma: float = 0.8,
    ci_order: int = 8,
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
        ci_length=ci_length,
        ci_gamma=ci_gamma,
        ci_order=ci_order,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
