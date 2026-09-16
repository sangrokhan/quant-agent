"""Strategy: SMA(trend_window) directional gate with continuous Kirshenbaum
Bands %B sizing overlay + deadband, leverage-cap-aware for crypto from the
start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Kirshenbaum Bands (Paul Kirshenbaum): channel lines drawn around an
exponential moving average, EMA(close, n), with the channel half-width set
to K * the standard error (stderr) of a linear regression of the trailing n
closes -- NOT a standard deviation like Bollinger Bands. Per
https://user42.tuxfamily.org/chart/manual/Kirshenbaum-Bands.html (Chart
Manual, read via browser_exec after the initial web_search backend call
succeeded for the keyword but did not surface a page web_extract could
render -- browser_exec used for the actual formula confirmation): "stderr is
based on deviation from a fitted sloping line, so if prices are making
steady progress up or down the channel width remains small" -- unlike
Bollinger's stddev-based width, which widens whenever a trend is in
progress. This is a genuinely distinct volatility-envelope construction
(regression-residual-based, not raw dispersion-based or ATR-based).

This repo has 1 prior Kirshenbaum entry (2026-09-08-021: EMA centerline +/-
stderr band, binary lower-band-touch entry gated by SMA(200) uptrend filter,
REJECTED -- full-sample Sharpe 0.53 fail, grid 4/72 pass, crypto 0/36). This
iteration reframes the same band as a Bollinger-%B-style CONTINUOUS SIZING
dial:
    kirsh_pctb = (close - lower) / (upper - lower)
naturally centered ~0.5 inside the band (can exceed [0,1] on band pierces),
rescaled via (pctb - 0.5) * 2 to a zero-centered dial, clipped to [-1, 1],
used as a sizing multiplier within an SMA(trend_window) uptrend gate --
following this cron trigger's validated continuous-sizing-dial pattern
(same technique already rescued STARC %B, Keltner %B, Bollinger %B,
Acceleration Bands, Elder AutoEnvelope, Standard Error Bands %B from prior
discrete-trigger rejections). Kirshenbaum %B has not previously been tested
this way in this repo -- distinct from Standard Error Bands (2026-09-14-147,
linear-regression ENDPOINT-anchored basis + smoothed standard error) since
Kirshenbaum centers on an EMA (not a linear-regression endpoint line).

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


def _rolling_linreg_stderr(close: pd.Series, window: int) -> pd.Series:
    """Standard error of a linear regression of close over trailing `window` bars."""
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    ss_xx = ((x - x_mean) ** 2).sum()

    def _stderr(y: np.ndarray) -> float:
        y_mean = y.mean()
        ss_xy = ((x - x_mean) * (y - y_mean)).sum()
        slope = ss_xy / ss_xx
        intercept = y_mean - slope * x_mean
        fitted = intercept + slope * x
        resid = y - fitted
        # standard error of the regression (residual std, ddof=2 for slope+intercept)
        if window <= 2:
            return np.nan
        return float(np.sqrt((resid ** 2).sum() / (window - 2)))

    return close.rolling(window).apply(_stderr, raw=True)


def _kirshenbaum_pctb(df: pd.DataFrame, ema_window: int, stderr_window: int, k: float) -> pd.Series:
    """Kirshenbaum %B: (close - lower) / (upper - lower).

    Upper/Lower = EMA(close, ema_window) +/- k * linreg_stderr(close, stderr_window).
    Naturally centered ~0.5 within the band; can exceed [0,1] on band pierces.
    """
    close = df["close"]
    centerline = close.ewm(span=ema_window, adjust=False, min_periods=ema_window).mean()
    stderr = _rolling_linreg_stderr(close, stderr_window)
    upper = centerline + k * stderr
    lower = centerline - k * stderr
    band_width = (upper - lower).replace(0.0, np.nan)
    pctb = (close - lower) / band_width
    return pctb


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
    kirsh_ema_window: int = 20,
    kirsh_stderr_window: int = 20,
    kirsh_k: float = 1.8,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Kirshenbaum %B is centered ~0.5; rescaled to a zero-centered dial via
    (pctb - 0.5) * 2, clipped to [-1, 1], then used as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    pctb = _kirshenbaum_pctb(df, kirsh_ema_window, kirsh_stderr_window, kirsh_k)
    pctb_centered = ((pctb - 0.5) * 2.0).clip(-1.0, 1.0)

    raw_exposure = base_exposure + sensitivity * pctb_centered
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    kirsh_ema_window: int = 20,
    kirsh_stderr_window: int = 20,
    kirsh_k: float = 1.8,
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
        kirsh_ema_window=kirsh_ema_window,
        kirsh_stderr_window=kirsh_stderr_window,
        kirsh_k=kirsh_k,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
