"""Strategy: NAGARCH (Engle & Ng 1993) shift-asymmetric volatility regime
gate + SMA trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per Engle & Ng (1993), formula confirmed via the `rugarch` R package
vignette (Section 2.2.6, fGARCH omnibus family -- same PDF already read
this cron trigger for the Component GARCH and TGARCH entries, third
distinct submodel definition consulted). Genuinely novel for this repo (0
prior "NAGARCH"/"Nonlinear Asymmetric GARCH" hits): NAGARCH arises from the
fGARCH omnibus formula with delta=lambda=2, eta1=0:

    sigma_t^2 = omega + alpha*(eps_{t-1} - eta2*sigma_{t-1})^2 + beta*sigma_{t-1}^2

This is a SHIFT-based asymmetry mechanism, structurally distinct from both
GJR-GARCH (indicator-function-based, already tested/rescued 2x this
trigger) and TGARCH (absolute-value-based, tested this same trigger,
2026-09-28-036): the innovation term is shifted by eta2*sigma_{t-1} BEFORE
squaring, so the "worst case" shock isn't at eps=0 but at
eps=eta2*sigma_{t-1} -- a continuous, smoothly-varying asymmetry (a
quadratic curve with its vertex shifted) rather than TGARCH's kinked
absolute-value response or GJR-GARCH's discontinuous indicator-function
jump. Applies this same cron trigger's own repeatedly-validated
trend-filter AND-gate pattern (7x confirmed this trigger).

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


def _fit_nagarch(log_ret: pd.Series):
    """Fit NAGARCH(1,1) (Engle & Ng 1993) via MLE (Normal innovations).
    Returns the in-sample sigma2_t series."""
    eps = log_ret.dropna().to_numpy()
    eps = eps - eps.mean()
    n = len(eps)
    var_est = np.var(eps)

    def neg_log_lik(params):
        omega, alpha, eta2, beta = params
        if omega <= 0 or alpha < 0 or beta < 0 or (alpha + beta) >= 1:
            return 1e10
        sigma2 = np.empty(n)
        sigma2[0] = var_est
        for t in range(1, n):
            sigma_prev = np.sqrt(sigma2[t - 1])
            sigma2[t] = omega + alpha * (eps[t - 1] - eta2 * sigma_prev) ** 2 + beta * sigma2[t - 1]
            if sigma2[t] <= 0 or not np.isfinite(sigma2[t]):
                return 1e10
        ll = -0.5 * (np.log(2 * np.pi) + np.log(sigma2) + eps ** 2 / sigma2)
        return -np.sum(ll)

    x0 = [var_est * 0.05, 0.05, 0.5, 0.85]
    try:
        res = minimize(neg_log_lik, x0, method="Nelder-Mead",
                        options={"maxiter": 3000, "xatol": 1e-7, "fatol": 1e-7})
        omega, alpha, eta2, beta = res.x
        if omega <= 0 or alpha < 0 or beta < 0 or (alpha + beta) >= 1:
            omega, alpha, eta2, beta = x0
    except Exception:
        omega, alpha, eta2, beta = x0

    sigma2 = np.empty(n)
    sigma2[0] = var_est
    for t in range(1, n):
        sigma_prev = np.sqrt(sigma2[t - 1])
        sigma2[t] = omega + alpha * (eps[t - 1] - eta2 * sigma_prev) ** 2 + beta * sigma2[t - 1]
        sigma2[t] = max(sigma2[t], 1e-12)

    idx = log_ret.dropna().index
    return pd.Series(sigma2, index=idx)


def _compute_signal_frame(price_df: pd.DataFrame, trend_window: int) -> pd.DataFrame:
    df = _prep(price_df)
    close = df["close"]
    log_ret = np.log(close.replace(0, np.nan)).diff()

    sigma2 = _fit_nagarch(log_ret)
    sigma2_shifted = sigma2.shift(1).reindex(df.index)

    sma = close.rolling(trend_window).mean()
    trend_up = close > sma

    out = pd.DataFrame({"sigma2": sigma2_shifted, "trend_up": trend_up}, index=df.index)
    return out


def generate_signals(
    price_df: pd.DataFrame,
    vol_threshold_quantile: float = 0.5,
    trend_window: int = 100,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a position series (0 or leverage_cap, long/flat). Long when
    the NAGARCH-implied conditional variance sigma2_t is below its own
    historical `vol_threshold_quantile` (calm regime) AND
    close > SMA(trend_window)."""
    df = _prep(price_df)
    sig = _compute_signal_frame(df, trend_window)
    sigma2 = sig["sigma2"]
    trend_up = sig["trend_up"]

    threshold = sigma2.quantile(vol_threshold_quantile)
    calm = sigma2 < threshold

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
