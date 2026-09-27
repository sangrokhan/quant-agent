"""Strategy: Component GARCH (Lee & Engle 1999) permanent-volatility regime
gate + SMA trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per Lee & Engle (1999), formula confirmed via the `rugarch` R package
vignette (Section 2.2.7 "The Component sGARCH model", CRAN,
https://cran.r-project.org/web/packages/rugarch/vignettes/Introduction_to_
the_rugarch_package.pdf, read via direct PDF text extraction after
web_extract's ddgs backend could not extract the PDF). Genuinely novel for
this repo (0 prior "Component GARCH"/"csGARCH"/"permanent and transitory
volatility" hits, distinct from the plain/GJR/EGARCH GARCH(1,1) models
already tested 4x this cron trigger, all of which assume a FIXED
unconditional long-run variance omega/(1-alpha-beta)):

    sigma_t^2 = q_t + alpha*(eps_{t-1}^2 - q_{t-1}) + beta*(sigma_{t-1}^2 - q_{t-1})   (transitory)
    q_t       = omega + rho*q_{t-1} + phi*(eps_{t-1}^2 - sigma_{t-1}^2)               (permanent)

The KEY structural distinction: q_t (the permanent/long-run component) is
itself a slowly-evolving random-walk-like process (rho close to 1), unlike
plain GARCH's fixed long-run variance. This gives TWO separately
interpretable volatility signals instead of one: the PERMANENT component
q_t (structural, slow-moving volatility regime) and the TRANSITORY
component (sigma_t^2 - q_t, fast mean-reverting volatility shocks). This
iteration gates on the PERMANENT component specifically (a calm STRUCTURAL
regime, not just a momentarily-quiet transitory blip) -- a genuinely
different regime-detection philosophy than the single-scale GARCH/GJR-
GARCH/EGARCH/HAR-D gates already tested. Applies this same cron trigger's
own repeatedly-validated trend-filter AND-gate pattern (5x confirmed:
GJR-GARCH, EGARCH, plain GARCH, HAR-D, CARR): AND the calm-permanent-
volatility gate with a plain close > SMA(trend_window) trend filter.

MLE fit (Normal innovations, same convention as this repo's other
from-scratch GARCH-family strategies) via `scipy.optimize.minimize`,
imposing the model's own stability constraints (alpha+beta<1, rho<1,
non-negativity), fit ONCE on the full available price history.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _fit_component_garch(log_ret: pd.Series):
    """Fit the Lee & Engle (1999) Component GARCH model via MLE (Normal
    innovations). Returns the full in-sample series of (sigma2_t, q_t)."""
    eps = log_ret.dropna().to_numpy()
    eps = eps - eps.mean()
    n = len(eps)
    var_est = np.var(eps)

    def unpack(params):
        omega, rho, phi, alpha, beta = params
        return omega, rho, phi, alpha, beta

    def neg_log_lik(params):
        omega, rho, phi, alpha, beta = unpack(params)
        if omega <= 0 or not (0 < rho < 1) or alpha < 0 or beta < 0 or (alpha + beta) >= 1:
            return 1e10
        q = np.empty(n)
        sigma2 = np.empty(n)
        q[0] = var_est
        sigma2[0] = var_est
        for t in range(1, n):
            q[t] = omega + rho * q[t - 1] + phi * (eps[t - 1] ** 2 - sigma2[t - 1])
            sigma2[t] = q[t] + alpha * (eps[t - 1] ** 2 - q[t - 1]) + beta * (sigma2[t - 1] - q[t - 1])
            if sigma2[t] <= 0 or not np.isfinite(sigma2[t]):
                return 1e10
        ll = -0.5 * (np.log(2 * np.pi) + np.log(sigma2) + eps ** 2 / sigma2)
        return -np.sum(ll)

    x0 = [var_est * 0.01, 0.99, 0.05, 0.05, 0.85]
    try:
        res = minimize(neg_log_lik, x0, method="Nelder-Mead",
                        options={"maxiter": 3000, "xatol": 1e-7, "fatol": 1e-7})
        omega, rho, phi, alpha, beta = res.x
        if omega <= 0 or not (0 < rho < 1) or alpha < 0 or beta < 0 or (alpha + beta) >= 1:
            omega, rho, phi, alpha, beta = x0
    except Exception:
        omega, rho, phi, alpha, beta = x0

    q = np.empty(n)
    sigma2 = np.empty(n)
    q[0] = var_est
    sigma2[0] = var_est
    for t in range(1, n):
        q[t] = omega + rho * q[t - 1] + phi * (eps[t - 1] ** 2 - sigma2[t - 1])
        sigma2[t] = q[t] + alpha * (eps[t - 1] ** 2 - q[t - 1]) + beta * (sigma2[t - 1] - q[t - 1])
        q[t] = max(q[t], 1e-12)
        sigma2[t] = max(sigma2[t], 1e-12)

    idx = log_ret.dropna().index
    return pd.Series(q, index=idx), pd.Series(sigma2, index=idx)


def _compute_signal_frame(price_df: pd.DataFrame, trend_window: int) -> pd.DataFrame:
    df = _prep(price_df)
    close = df["close"]
    log_ret = np.log(close.replace(0, np.nan)).diff()

    q, sigma2 = _fit_component_garch(log_ret)
    # No look-ahead: today's regime gate uses YESTERDAY's fitted permanent
    # component (the forecast made at the close of t-1).
    q_shifted = q.shift(1).reindex(df.index)

    sma = close.rolling(trend_window).mean()
    trend_up = close > sma

    out = pd.DataFrame({"q": q_shifted, "trend_up": trend_up}, index=df.index)
    return out


def generate_signals(
    price_df: pd.DataFrame,
    vol_threshold_quantile: float = 0.5,
    trend_window: int = 100,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a position series (0 or leverage_cap, long/flat). Long when
    the Component GARCH's PERMANENT (long-run structural) volatility
    component q_t is below its own historical `vol_threshold_quantile` (a
    calm STRUCTURAL regime, not just a quiet transitory blip) AND
    close > SMA(trend_window) -- the trend-filter AND-gate fix validated
    5x this cron trigger on other volatility-regime-gate strategies.
    `leverage_cap` scales exposure (<=1.0 caps high-vol assets like
    crypto, matching this repo's other crypto-leg leverage-cap
    convention)."""
    df = _prep(price_df)
    sig = _compute_signal_frame(df, trend_window)
    q = sig["q"]
    trend_up = sig["trend_up"]

    threshold = q.quantile(vol_threshold_quantile)
    calm = q < threshold

    position = (calm & trend_up).fillna(False).astype(float) * leverage_cap
    return position


def generate_returns(
    price_df: pd.DataFrame,
    vol_threshold_quantile: float = 0.5,
    trend_window: int = 100,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df, vol_threshold_quantile=vol_threshold_quantile, trend_window=trend_window,
        leverage_cap=leverage_cap,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
