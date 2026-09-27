"""Strategy: apARCH (Ding, Granger & Engle 1993) free-power asymmetric
volatility regime gate + SMA trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per Ding, Granger & Engle (1993), formula confirmed via the `rugarch` R
package vignette (Section 2.2.5, apARCH -- same PDF already read this cron
trigger for the Component GARCH, TGARCH, and NAGARCH entries, fourth
distinct submodel consulted). Genuinely novel for this repo (0 prior
"apARCH"/"asymmetric power ARCH" hits -- distinct from TGARCH, delta fixed
at 1, and GJR-GARCH/plain GARCH, delta fixed at 2, both already tested this
same cron trigger):

    sigma_t^delta = omega + alpha*(|eps_{t-1}| - gamma*eps_{t-1})^delta + beta*sigma_{t-1}^delta

The KEY structural distinction: delta is a FREE Box-Cox power parameter,
fit via MLE jointly with the other parameters (not fixed a priori like
every other GARCH-family variant tested this trigger). Named after the
Taylor (1986) effect, cited in the rugarch vignette: the sample
autocorrelation of ABSOLUTE returns often exceeds that of SQUARED returns,
suggesting the "correct" power to raise volatility shocks to for best
persistence/fit may not be exactly 2 (as plain GARCH/GJR-GARCH assume) or
exactly 1 (as TGARCH/AVGARCH assume), but somewhere in between (or
outside) that range, and the data itself should determine it. Applies this
same cron trigger's own 8x-validated trend-filter AND-gate pattern.

MLE fit (Normal innovations, same convention as this repo's other
from-scratch GARCH-family strategies) via `scipy.optimize.minimize`,
imposing alpha+beta<1, delta in a sensible positive range, fit ONCE on the
full available price history.

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


def _fit_aparch(log_ret: pd.Series):
    """Fit apARCH(1,1) (Ding, Granger & Engle 1993) via MLE (Normal
    innovations), with delta as a FREE parameter. Returns the in-sample
    sigma_t series (conditional std, sigma_t^delta -> sigma_t via
    delta-th root)."""
    eps = log_ret.dropna().to_numpy()
    eps = eps - eps.mean()
    n = len(eps)
    abs_mean = np.mean(np.abs(eps))

    def neg_log_lik(params):
        omega, alpha, gamma, beta, delta = params
        if (omega <= 0 or alpha < 0 or beta < 0 or (alpha + beta) >= 1
                or abs(gamma) > 1 or delta <= 0.2 or delta > 4):
            return 1e10
        sigma_pow = np.empty(n)
        sigma_pow[0] = abs_mean ** delta
        for t in range(1, n):
            shock = abs(eps[t - 1]) - gamma * eps[t - 1]
            if shock < 0:
                shock = 0.0
            sigma_pow[t] = omega + alpha * (shock ** delta) + beta * sigma_pow[t - 1]
            if sigma_pow[t] <= 0 or not np.isfinite(sigma_pow[t]):
                return 1e10
        sigma = sigma_pow ** (1.0 / delta)
        ll = -0.5 * (np.log(2 * np.pi) + 2 * np.log(sigma) + (eps / sigma) ** 2)
        return -np.sum(ll)

    x0 = [abs_mean ** 2 * 0.05, 0.1, 0.1, 0.8, 2.0]
    try:
        res = minimize(neg_log_lik, x0, method="Nelder-Mead",
                        options={"maxiter": 4000, "xatol": 1e-7, "fatol": 1e-7})
        omega, alpha, gamma, beta, delta = res.x
        if (omega <= 0 or alpha < 0 or beta < 0 or (alpha + beta) >= 1
                or abs(gamma) > 1 or delta <= 0.2 or delta > 4):
            omega, alpha, gamma, beta, delta = x0
    except Exception:
        omega, alpha, gamma, beta, delta = x0

    sigma_pow = np.empty(n)
    sigma_pow[0] = abs_mean ** delta
    for t in range(1, n):
        shock = abs(eps[t - 1]) - gamma * eps[t - 1]
        if shock < 0:
            shock = 0.0
        sigma_pow[t] = omega + alpha * (shock ** delta) + beta * sigma_pow[t - 1]
        sigma_pow[t] = max(sigma_pow[t], 1e-12)
    sigma = sigma_pow ** (1.0 / delta)

    idx = log_ret.dropna().index
    return pd.Series(sigma, index=idx)


def _compute_signal_frame(price_df: pd.DataFrame, trend_window: int) -> pd.DataFrame:
    df = _prep(price_df)
    close = df["close"]
    log_ret = np.log(close.replace(0, np.nan)).diff()

    sigma = _fit_aparch(log_ret)
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
    the apARCH-implied conditional std sigma_t is below its own historical
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
