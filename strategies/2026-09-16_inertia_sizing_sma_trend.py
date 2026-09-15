"""Strategy: SMA(trend_window) directional gate with continuous Dorsey
Inertia (linear-regression-smoothed RVI) sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Inertia (Donald Dorsey, "Refining the Relative Volatility Index", S&C Sep
1995): the Relative Volatility Index (RVI, this repo's own established
formula from 2026-09-05-003/2026-09-14-142: RVI = 100*EMA(up_stdev) /
(EMA(up_stdev)+EMA(down_stdev)), naturally bounded [0,100], midline 50),
further smoothed by a rolling LINEAR REGRESSION (the "inertia" concept --
Dorsey's own stated rationale: "a trend is simply the outward result of
inertia... the market will require much more energy to reverse its
direction than to extend the ongoing move", per
https://www.tradingpedia.com/forex-trading-indicators/inertia-indicator,
visited this iteration via browser_exec).

Repo has 1 prior Inertia entry (2026-09-12-151, midline-crossover binary
trigger, decisively rejected -- Sharpe/MDD/TC-survival all fail full-
sample despite a strong low-vol-regime edge that didn't generalize). This
iteration reframes Inertia as a CONTINUOUS SIZING dial (rescaled from
[0,100] to [-1,+1] around its natural midline of 50, same pattern already
validated for the plain-RVI continuous-sizing entry 2026-09-14-142) rather
than a binary midline-crossover trigger, inside the existing
SMA(trend_window) uptrend gate with a deadband, leverage-cap-aware for
crypto from the start. First Inertia continuous-sizing variant in this
repo.

Source: https://www.tradingpedia.com/forex-trading-indicators/inertia-indicator
(qualitative construction/rationale) and this repo's own established RVI
formula (2026-09-05-003/2026-09-14-142, reused unchanged), visited via
browser_exec this iteration (web_search returned only tangential results
for the direct "Inertia indicator" query, browser_exec Google SERP
surfaced tradingpedia.com/tradingview.com/csidata.com corroborating
sources).

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


def _relative_volatility_index(
    close: pd.Series, rvi_window: int, rvi_smooth: int
) -> pd.Series:
    stdev = close.rolling(rvi_window, min_periods=max(2, rvi_window // 2)).std()
    up_move = close.diff() > 0
    up_stdev = stdev.where(up_move, 0.0)
    down_stdev = stdev.where(~up_move, 0.0)

    up_ema = up_stdev.ewm(span=rvi_smooth, adjust=False).mean()
    down_ema = down_stdev.ewm(span=rvi_smooth, adjust=False).mean()

    denom = (up_ema + down_ema).replace(0.0, np.nan)
    rvi = 100.0 * up_ema / denom
    return rvi.fillna(50.0)


def _linreg_endpoint(series: pd.Series, window: int) -> pd.Series:
    """Rolling linear-regression forecast (endpoint) over `window` bars,
    the "inertia" smoothing step per Dorsey's original construction."""
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()

    def _endpoint(y: np.ndarray) -> float:
        y_mean = y.mean()
        slope = ((x - x_mean) * (y - y_mean)).sum() / x_var
        intercept = y_mean - slope * x_mean
        return intercept + slope * x[-1]

    return series.rolling(window).apply(_endpoint, raw=True)


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
    rvi_window: int = 10,
    rvi_smooth: int = 14,
    linreg_window: int = 20,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Inertia (RVI further smoothed by a rolling linear-regression endpoint)
    is naturally bounded [0,100]; rescaled to [-1,+1] via (Inertia-50)/50
    (centered on Dorsey's own midline), then used directly as a sizing
    dial gated by an SMA(trend_window) uptrend filter.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    rvi = _relative_volatility_index(close, rvi_window, rvi_smooth)
    inertia = _linreg_endpoint(rvi, linreg_window)
    inertia_centered = ((inertia - 50.0) / 50.0).fillna(0.0)

    raw_exposure = base_exposure + sensitivity * inertia_centered
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    rvi_window: int = 10,
    rvi_smooth: int = 14,
    linreg_window: int = 20,
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
        rvi_window=rvi_window,
        rvi_smooth=rvi_smooth,
        linreg_window=linreg_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
