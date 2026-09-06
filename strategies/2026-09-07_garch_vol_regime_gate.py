"""Strategy: GARCH(1,1) conditional-volatility regime gate (long/flat).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-015):
Per https://www.quantopia.net/time-series/garch-volatility: GARCH(1,1)
models time-varying conditional variance as
    sigma_t^2 = omega + alpha * eps_{t-1}^2 + beta * sigma_{t-1}^2
capturing volatility clustering and mean-reversion with only 3 parameters.
The source's own cited real-world use case: "Volatility Targeting
Strategies: Robo-advisors use GARCH forecasts to automatically adjust
portfolio allocations: if GARCH equity volatility exceeds [a threshold],
the portfolio shifts... to keep overall portfolio volatility at a target
annualized level." Operationalized here as a binary long/flat regime gate:
stay long the underlying while the GARCH(1,1)-forecast annualized
conditional volatility is below a threshold (calm, "risk-on" regime); go
flat when the forecast crosses above the threshold (turbulent, "risk-off"
regime). This differs from every existing realized-vol-regime filter in
this repo (e.g. 2026-09-03-001's Bollinger strategy, which gates on a
simple trailing rolling standard deviation vs. its own trailing median) by
using a genuinely fitted conditional-variance model with persistence
(alpha+beta) and mean-reversion (omega), which reacts to volatility shocks
(large |eps|) immediately rather than only after they roll into a trailing
window average.

Signal logic
------------
- GARCH(1,1) is refit via MLE (scipy.optimize.minimize) periodically (every
  `refit_every` trading days, not every bar, to keep runtime tractable) on
  the trailing `lookback` daily log returns (scaled by 100 per standard
  GARCH-fitting practice).
- Forecast annualized conditional vol for the day AFTER each refit:
  vol_ann = sqrt(sigma_t^2 * 252) / 100, held constant until the next
  refit (a coarse but tractable approximation to daily re-forecasting).
- Long (position=1) when the current forecast vol_ann <= vol_threshold.
- Flat (position=0) when forecast vol_ann > vol_threshold.
- No time-stop needed -- this is a pure regime gate on a buy-and-hold base
  position, not a discrete entry/exit trade signal.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _garch11_neg_loglik(params, eps):
    omega, alpha, beta = params
    if omega <= 0 or alpha < 0 or beta < 0 or (alpha + beta) >= 1:
        return 1e10
    n = len(eps)
    sigma2 = np.empty(n)
    sigma2[0] = np.var(eps)
    for t in range(1, n):
        sigma2[t] = omega + alpha * eps[t - 1] ** 2 + beta * sigma2[t - 1]
    sigma2 = np.maximum(sigma2, 1e-8)
    ll = -0.5 * np.sum(np.log(2 * np.pi * sigma2) + (eps ** 2) / sigma2)
    return -ll


def _fit_garch11(eps: np.ndarray):
    """Fit GARCH(1,1) via MLE; return (omega, alpha, beta, last_sigma2)."""
    var0 = float(np.var(eps)) if len(eps) > 1 else 1.0
    x0 = [max(var0 * 0.05, 1e-4), 0.05, 0.90]
    bounds = [(1e-6, None), (0.0, 0.999), (0.0, 0.999)]
    try:
        res = minimize(
            _garch11_neg_loglik, x0, args=(eps,), method="L-BFGS-B", bounds=bounds
        )
        omega, alpha, beta = res.x
    except Exception:
        omega, alpha, beta = x0
    if alpha + beta >= 1:
        beta = max(0.0, 0.99 - alpha)
    n = len(eps)
    sigma2 = np.empty(n)
    sigma2[0] = var0
    for t in range(1, n):
        sigma2[t] = omega + alpha * eps[t - 1] ** 2 + beta * sigma2[t - 1]
    return omega, alpha, beta, sigma2[-1], eps[-1]


def generate_signals(
    price_df: pd.DataFrame,
    lookback: int = 250,
    refit_every: int = 21,
    vol_threshold: float = 0.25,
) -> pd.Series:
    """Return a {0,1} long/flat position series (GARCH vol regime gate)."""
    df = _prep(price_df)
    close = df["close"]
    log_ret = np.log(close / close.shift(1)).fillna(0.0)
    ret_pct = (log_ret * 100).values  # scale for GARCH fitting stability

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)

    current_vol_ann = None
    for i in range(n):
        if i >= lookback and (i % refit_every == 0 or current_vol_ann is None):
            window = ret_pct[max(0, i - lookback) : i]
            if len(window) >= 30:
                omega, alpha, beta, last_sigma2, last_eps = _fit_garch11(window)
                # one-step-ahead forecast
                fcast_sigma2 = omega + alpha * last_eps ** 2 + beta * last_sigma2
                current_vol_ann = np.sqrt(max(fcast_sigma2, 1e-8) * 252) / 100.0
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
