"""Strategy: SMA(trend_window) directional gate with continuous Twiggs
Money Flow (true-range-based, EMA-smoothed) sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
Twiggs Money Flow (Colin Twiggs; formula per
https://www.incrediblecharts.com/indicators/twiggs_money_flow.php, read
this iteration via browser_exec fallback -- web_search's DuckDuckGo
backend TLS-errored on every query attempted this iteration): a
refinement of Chaikin Money Flow that (1) uses TRUE RANGE (accounting for
gaps: TrueRangeHigh=max(High,PrevClose), TrueRangeLow=min(Low,PrevClose))
instead of the plain daily High-Low range, and (2) applies EXPONENTIAL
smoothing (Wilder-style) rather than a rolling sum/average, avoiding the
CMF "bark twice" artifact where an old extreme datapoint dropping out of a
fixed-length sum window causes a spurious jump unrelated to current
price/volume. Source's own stated signal rule: "the higher the reading
(above or below zero), the stronger the signal" -- TMF is naturally
bounded roughly [-1, 1] like CMF, explicitly amenable to graded/continuous
interpretation rather than only a zero-line threshold.

This repo has 3 prior Twiggs Money Flow entries (2026-09-05-002 zero-line
cross + pullback timing, 2026-09-06-143 EMA-signal-line cross, both
rejected as binary triggers), plus this cron trigger's own CMF continuous-
sizing-dial precedent (2026-09-13-090, accepted). This iteration is the
first to combine Twiggs' true-range + EMA-smoothing refinements with the
continuous-sizing-dial reframing -- directly testing whether TMF's gap-
handling/smoothing improvements (vs plain CMF) carry through to a better
or more stable sizing signal, not just a marginally different binary
threshold.

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


def _twiggs_money_flow(df: pd.DataFrame, window: int = 21) -> pd.Series:
    """TMF = EMA(ADV, window) / EMA(Volume, window).

    ADV[t] = ((Close[t]-TrueRangeLow[t]) - (TrueRangeHigh[t]-Close[t])) /
             (TrueRangeHigh[t]-TrueRangeLow[t]) * Volume[t]
    TrueRangeHigh[t] = max(High[t], Close[t-1]); TrueRangeLow[t] =
    min(Low[t], Close[t-1]) -- accounts for gaps, unlike plain CMF's
    High/Low. Naturally bounded ~[-1, 1] by construction (same
    ratio-of-volume-weighted-position-in-range idea as CMF, EMA-smoothed
    per Wilder's convention instead of a rolling sum).
    """
    high, low, close, volume = df["high"], df["low"], df["close"], df["volume"]
    prev_close = close.shift(1)
    tr_high = pd.concat([high, prev_close], axis=1).max(axis=1)
    tr_low = pd.concat([low, prev_close], axis=1).min(axis=1)
    tr_range = (tr_high - tr_low).replace(0, np.nan)

    adv = ((close - tr_low) - (tr_high - close)) / tr_range * volume
    tmf = adv.ewm(span=window, adjust=False).mean() / volume.ewm(span=window, adjust=False).mean()
    return tmf.clip(lower=-1.0, upper=1.0)


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
    tmf_window: int = 21,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    tmf = _twiggs_money_flow(df, window=tmf_window)

    raw_exposure = base_exposure + sensitivity * tmf
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    tmf_window: int = 21,
    base_exposure: float = 0.5,
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
        tmf_window=tmf_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
