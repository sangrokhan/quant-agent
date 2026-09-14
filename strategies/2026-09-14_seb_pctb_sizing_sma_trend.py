"""Strategy: SMA(trend_window) directional gate with continuous Standard
Error Bands (SEB) %B sizing overlay + deadband, leverage-cap-aware for
crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Standard Error Bands (SEB, Jon Andersen, TASC Sep 1996): a linear-regression
envelope, distinct from Bollinger Bands (std-dev around a moving average)
and from STARC Bands (ATR around an SMA, already tested this cron trigger
as 2026-09-14-144) -- SEB measures SCATTER of price around a fitted linear
regression line via the standard error of the estimate:
    Basis = SMA(3, LinRegEndpoint(close, 21))
    Upper = Basis + K * SmoothedStandardError
    Lower = Basis - K * SmoothedStandardError
Per Jon Andersen's classic parameters (21-period regression, 3-period SMA
smoothing, K=2), confirmed via Google AI-overview synthesis of
TASC/LuxAlgo/Commodity.com (browser_exec fallback -- web_search's DDGS
backend was not attempted successfully for a clean formula this iteration,
so browser_exec was used directly per the "if web_search struggles, prefer
the reliable fallback" guidance).

This repo has 3 prior SEB entries: band-breakout (rejected), pullback-to-
centerline (rejected), and band-touch-reversal mean-reversion (accepted,
QQQ-only, decisively fails crypto). None used SEB as a CONTINUOUS SIZING
dial. This iteration reframes SEB the same way STARC (2026-09-14-144) was
reframed: seb_pctb = (close - lower) / (upper - lower), naturally centered
~0.5, rescaled to a zero-centered [-1,+1] dial, used as a sizing multiplier
within an SMA(trend_window) uptrend gate. First SEB continuous-sizing
variant in this repo.

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


def _linreg_endpoint_and_stderr(close: pd.Series, window: int):
    """Rolling linear-regression endpoint value and standard error of the
    estimate, both computed over `window`-bar trailing windows.
    """
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    x_demeaned = x - x_mean
    denom = (x_demeaned ** 2).sum()

    def _endpoint(y: np.ndarray) -> float:
        y_mean = y.mean()
        slope = float((x_demeaned * (y - y_mean)).sum() / denom)
        intercept = y_mean - slope * x_mean
        return intercept + slope * x[-1]

    def _stderr(y: np.ndarray) -> float:
        y_mean = y.mean()
        slope = float((x_demeaned * (y - y_mean)).sum() / denom)
        intercept = y_mean - slope * x_mean
        fitted = intercept + slope * x
        resid = y - fitted
        # standard error of the estimate (n-2 degrees of freedom)
        return float(np.sqrt((resid ** 2).sum() / max(window - 2, 1)))

    endpoint = close.rolling(window).apply(_endpoint, raw=True)
    stderr = close.rolling(window).apply(_stderr, raw=True)
    return endpoint, stderr


def _seb_pctb(df: pd.DataFrame, lr_window: int, smooth_window: int, k: float) -> pd.Series:
    """SEB %B: (close - lower) / (upper - lower), naturally centered ~0.5."""
    close = df["close"]
    endpoint, stderr = _linreg_endpoint_and_stderr(close, lr_window)
    basis = endpoint.rolling(smooth_window).mean()
    smoothed_se = stderr.rolling(smooth_window).mean()
    upper = basis + k * smoothed_se
    lower = basis - k * smoothed_se
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
    seb_lr_window: int = 21,
    seb_smooth_window: int = 3,
    seb_k: float = 2.0,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    pctb = _seb_pctb(df, seb_lr_window, seb_smooth_window, seb_k)
    pctb_centered = ((pctb - 0.5) * 2.0).clip(-1.0, 1.0)

    raw_exposure = base_exposure + sensitivity * pctb_centered
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    seb_lr_window: int = 21,
    seb_smooth_window: int = 3,
    seb_k: float = 2.0,
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
        seb_lr_window=seb_lr_window,
        seb_smooth_window=seb_smooth_window,
        seb_k=seb_k,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
