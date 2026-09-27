"""Strategy: TGARCH (Zakoian 1994) absolute-value asymmetric volatility
regime gate + SMA trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per Zakoian (1994), formula confirmed via the `rugarch` R package vignette
(Section 2.2.5/2.2.6, apARCH/fGARCH families -- CRAN, same PDF already
read this cron trigger for the Component GARCH entry, re-consulted for a
different submodel definition, corroborated via Google SERP snippets from
didattica.unibocconi.it and dspace.ut.ee lecture notes). Genuinely novel
for this repo (0 prior "TGARCH"/"threshold GARCH" hits): TGARCH models the
CONDITIONAL STANDARD DEVIATION directly (not the variance) via ABSOLUTE-
VALUE shocks with an asymmetric leverage term:

    sigma_t = omega + alpha*(|eps_{t-1}| - gamma*eps_{t-1}) + beta*sigma_{t-1}

This is a special case of the apARCH family with delta=1 (power on sigma,
not sigma^2, unlike GJR-GARCH's delta=2/squared-variance formulation
already tested/rescued 2x this trigger). The (|eps|-gamma*eps) term makes
negative shocks (eps<0) contribute MORE to sigma_t than positive shocks of
the same magnitude when gamma>0 (the "leverage effect": bad news increases
volatility more than good news) -- structurally distinct from GJR-GARCH's
indicator-function-based asymmetry (I(eps<0)*eps^2). Applies this same
cron trigger's own repeatedly-validated trend-filter AND-gate pattern (6x
confirmed this trigger: GJR-GARCH, EGARCH, plain GARCH, HAR-D, CARR,
Component GARCH): AND the calm-volatility gate (fitted sigma_t below a
threshold) with a plain close > SMA(trend_window) trend filter.

MLE fit (Normal innovations, same convention as this repo's other
from-scratch GARCH-family strategies) via `scipy.optimize.minimize`,
imposing alpha+beta<1, fit ONCE on the full available price history.

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


def _fit_tgarch(log_ret: pd.Series):
    """Fit TGARCH(1,1) (Zakoian 1994) via MLE (Normal innovations on
    eps/sigma). Returns the in-sample sigma_t series."""
    eps = log_ret.dropna().to_numpy()
    eps = eps - eps.mean()
    n = len(eps)
    abs_mean = np.mean(np.abs(eps))

    def neg_log_lik(params):
        omega, alpha, gamma, beta = params
        if omega <= 0 or alpha < 0 or beta < 0 or (alpha + beta) >= 1 or abs(gamma) > 1:
            return 1e10
        sigma = np.empty(n)
        sigma[0] = abs_mean
        for t in range(1, n):
            sigma[t] = omega + alpha * (abs(eps[t - 1]) - gamma * eps[t - 1]) + beta * sigma[t - 1]
            if sigma[t] <= 0 or not np.isfinite(sigma[t]):
                return 1e10
        z = eps / sigma
        ll = -0.5 * (np.log(2 * np.pi) + 2 * np.log(sigma) + z ** 2)
        return -np.sum(ll)

    x0 = [abs_mean * 0.1, 0.1, 0.1, 0.8]
    try:
        res = minimize(neg_log_lik, x0, method="Nelder-Mead",
                        options={"maxiter": 3000, "xatol": 1e-7, "fatol": 1e-7})
        omega, alpha, gamma, beta = res.x
        if omega <= 0 or alpha < 0 or beta < 0 or (alpha + beta) >= 1 or abs(gamma) > 1:
            omega, alpha, gamma, beta = x0
    except Exception:
        omega, alpha, gamma, beta = x0

    sigma = np.empty(n)
    sigma[0] = abs_mean
    for t in range(1, n):
        sigma[t] = omega + alpha * (abs(eps[t - 1]) - gamma * eps[t - 1]) + beta * sigma[t - 1]
        sigma[t] = max(sigma[t], 1e-12)

    idx = log_ret.dropna().index
    return pd.Series(sigma, index=idx)


def _compute_signal_frame(price_df: pd.DataFrame, trend_window: int) -> pd.DataFrame:
    df = _prep(price_df)
    close = df["close"]
    log_ret = np.log(close.replace(0, np.nan)).diff()

    sigma = _fit_tgarch(log_ret)
    sigma_shifted = sigma.shift(1).reindex(df.index)

    sma = close.rolling(trend_window).mean()
    trend_up = close > sma

    out = pd.DataFrame({"sigma": sigma_shifted, "trend_up": trend_up}, index=df.index)
    return out


def generate_signals(
    price_df: pd.DataFrame,
    vol_threshold_quantile: float = 0.5,
    trend_window: int = 100,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a position series (0 or leverage_cap, long/flat). Long when
    the TGARCH-implied conditional std sigma_t is below its own historical
    `vol_threshold_quantile` (calm regime) AND close > SMA(trend_window)."""
    df = _prep(price_df)
    sig = _compute_signal_frame(df, trend_window)
    sigma = sig["sigma"]
    trend_up = sig["trend_up"]

    threshold = sigma.quantile(vol_threshold_quantile)
    calm = sigma < threshold

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
