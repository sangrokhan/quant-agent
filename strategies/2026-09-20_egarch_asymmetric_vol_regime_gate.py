"""Strategy: EGARCH(1,1) asymmetric conditional-volatility regime gate.

Hypothesis (grounded in this iteration's research; see e.g.
https://vlab.stern.nyu.edu/docs/volatility/EGARCH and multiple corroborating
sources found via Google search this iteration -- Medium's "Advanced GARCH
Models: EGARCH and GJR-GARCH", MetricGate's "EGARCH Model Explained"):

Nelson's EGARCH(1,1) models log-conditional-variance as
    ln(sigma_t^2) = omega + beta*ln(sigma_{t-1}^2)
                    + alpha*(|z_{t-1}| - E|z|) + gamma*z_{t-1}
where z_{t-1} = eps_{t-1}/sigma_{t-1} is the standardized residual. The
gamma term captures the "leverage effect": negative shocks (z<0) increase
future conditional volatility MORE than positive shocks of the same
magnitude (gamma<0 typically for equities). This repo already tested a
plain symmetric GARCH(1,1) vol-regime gate (2026-09-07-015, near-miss,
full-sample Sharpe QQQ 0.811/SPY 0.714) that treats positive and negative
shocks identically. EGARCH's asymmetric leverage term should, per the
source material's own stated mechanism, react faster and more accurately
to the down-shocks that actually precede volatility spikes (vs GARCH's
symmetric eps^2 term, which under-reacts to a large down-move relative to
an equally large up-move) -- so the EGARCH-forecast regime gate should
produce a cleaner "stay in / get out before the vol spike" signal than the
plain-GARCH near-miss.

Signal logic
------------
- EGARCH(1,1) parameters (omega, alpha, beta, gamma) fit via MLE
  (scipy.optimize.minimize) on the trailing `lookback` daily log returns
  (scaled x100 for numerical stability), refit every `refit_every` trading
  days (not every bar, for tractable runtime).
- One-step-ahead forecast annualized conditional vol computed after each
  refit, held constant until the next refit (same coarse-but-tractable
  approximation as the existing plain-GARCH strategy in this repo).
- Long (position=1) when forecast vol_ann <= `vol_threshold` (calm regime).
- Flat (position=0) when forecast vol_ann > `vol_threshold` (turbulent
  regime, EGARCH's asymmetric leverage term should flag this earlier after
  a down-shock than the symmetric GARCH would).
- Pure regime gate on a buy-and-hold base position -- no separate
  entry/exit trade logic or time-stop needed.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

_E_ABS_Z = np.sqrt(2.0 / np.pi)  # E|z| for standard normal z


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _egarch_log_sigma2(params, eps):
    omega, alpha, beta, gamma = params
    n = len(eps)
    log_sigma2 = np.empty(n)
    var0 = float(np.var(eps)) if n > 1 else 1.0
    log_sigma2[0] = np.log(max(var0, 1e-8))
    sigma = np.empty(n)
    sigma[0] = np.sqrt(max(var0, 1e-8))
    for t in range(1, n):
        z_prev = eps[t - 1] / sigma[t - 1] if sigma[t - 1] > 0 else 0.0
        log_sigma2[t] = (
            omega
            + beta * log_sigma2[t - 1]
            + alpha * (abs(z_prev) - _E_ABS_Z)
            + gamma * z_prev
        )
        log_sigma2[t] = np.clip(log_sigma2[t], -20, 20)
        sigma[t] = np.sqrt(np.exp(log_sigma2[t]))
    return log_sigma2, sigma


def _egarch_neg_loglik(params, eps):
    omega, alpha, beta, gamma = params
    if abs(beta) >= 1.0 or alpha < 0:
        return 1e10
    log_sigma2, _ = _egarch_log_sigma2(params, eps)
    sigma2 = np.exp(np.clip(log_sigma2, -20, 20))
    ll = -0.5 * np.sum(np.log(2 * np.pi * sigma2) + (eps ** 2) / sigma2)
    if not np.isfinite(ll):
        return 1e10
    return -ll


def _fit_egarch11(eps: np.ndarray):
    """Fit EGARCH(1,1) via MLE; return (omega, alpha, beta, gamma,
    last_log_sigma2, last_eps, last_sigma)."""
    var0 = float(np.var(eps)) if len(eps) > 1 else 1.0
    x0 = [np.log(max(var0, 1e-4)) * 0.1, 0.1, 0.9, -0.05]
    bounds = [(-5, 5), (0.0, 1.0), (-0.999, 0.999), (-1.0, 1.0)]
    try:
        res = minimize(
            _egarch_neg_loglik, x0, args=(eps,), method="L-BFGS-B", bounds=bounds
        )
        omega, alpha, beta, gamma = res.x
    except Exception:
        omega, alpha, beta, gamma = x0
    log_sigma2, sigma = _egarch_log_sigma2((omega, alpha, beta, gamma), eps)
    return omega, alpha, beta, gamma, log_sigma2[-1], eps[-1], sigma[-1]


def generate_signals(
    price_df: pd.DataFrame,
    lookback: int = 250,
    refit_every: int = 21,
    vol_threshold: float = 0.25,
) -> pd.Series:
    """Return a {0,1} long/flat position series (EGARCH vol regime gate)."""
    df = _prep(price_df)
    close = df["close"]
    log_ret = np.log(close / close.shift(1)).fillna(0.0)
    ret_pct = (log_ret * 100).values

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)

    current_vol_ann = None
    for i in range(n):
        if i >= lookback and (i % refit_every == 0 or current_vol_ann is None):
            window = ret_pct[max(0, i - lookback) : i]
            if len(window) >= 30:
                omega, alpha, beta, gamma, last_log_sigma2, last_eps, last_sigma = _fit_egarch11(window)
                z_last = last_eps / last_sigma if last_sigma > 0 else 0.0
                fcast_log_sigma2 = (
                    omega
                    + beta * last_log_sigma2
                    + alpha * (abs(z_last) - _E_ABS_Z)
                    + gamma * z_last
                )
                fcast_sigma2 = np.exp(np.clip(fcast_log_sigma2, -20, 20))
                current_vol_ann = np.sqrt(fcast_sigma2 * 252) / 100.0
        if current_vol_ann is not None:
            position.iloc[i] = 1 if current_vol_ann <= vol_threshold else 0
        else:
            position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
