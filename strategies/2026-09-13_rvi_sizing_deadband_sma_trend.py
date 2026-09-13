"""Strategy: SMA200 trend-following gate with continuous Relative Vigor
Index (RVI) sizing overlay, with an exposure-change deadband baked in from
the start.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-13-081):
Relative Vigor Index (RVI, John Ellis) = triangle-weighted 4-period average
of (Close-Open)/(High-Low), naturally bounded roughly in [-1, 1] since each
period's raw ratio is bounded there and it's a weighted average. Per
bybit.com/tradingsim.com/steema.com/investopedia.com (browser_exec SERP
synthesis this iteration -- web_search DDGS backend returned "no results
found" for this exact query, google.com fallback used). Repo has 8 prior
RVI entries, all binary signal-line-crossover entry triggers -- zero as a
continuous sizing dial. This iteration reuses the "bounded oscillator as
continuous sizing dial + exposure-change deadband" pattern validated 3x
already this cron trigger (CMO 2026-09-13-078, Ultimate Oscillator
2026-09-13-079, StochRSI 2026-09-13-080): exposure = clip(base_exposure +
rvi_sensitivity * rvi, 0, leverage_cap) on the SMA(200) trend gate, held
within `deadband` of the last update. RVI is structurally distinct from
every prior sizing dial tried this trigger -- it measures INTRADAY
close-vs-open conviction relative to the day's range (candle-body-based),
not a price-band position, extreme-recency count, or momentum sum/ratio.
First RVI-as-continuous-sizing strategy in this repo.

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


def _rvi(df: pd.DataFrame, window: int = 10) -> pd.Series:
    close = df["close"]
    open_ = df["open"]
    high = df["high"]
    low = df["low"]

    a = close - open_
    b = high - low

    # Triangle-weighted 4-period smoothing per the standard RVI construction
    # (weights 1,2,2,1 over the current and prior 3 bars), then a rolling
    # mean over `window` periods for extra smoothing/normalization.
    num = (a + 2 * a.shift(1) + 2 * a.shift(2) + a.shift(3)) / 6.0
    den = (b + 2 * b.shift(1) + 2 * b.shift(2) + b.shift(3)) / 6.0
    rvi_raw = num / den.replace(0, np.nan)
    rvi = rvi_raw.rolling(window).mean()
    return rvi.clip(lower=-1.0, upper=1.0)


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
    trend_window: int = 200,
    rvi_window: int = 10,
    base_exposure: float = 0.8,
    rvi_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    rvi = _rvi(df, window=rvi_window)

    raw_exposure = base_exposure + rvi_sensitivity * rvi
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    rvi_window: int = 10,
    base_exposure: float = 0.8,
    rvi_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        rvi_window=rvi_window,
        base_exposure=base_exposure,
        rvi_sensitivity=rvi_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
