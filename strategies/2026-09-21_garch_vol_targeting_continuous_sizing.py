"""Strategy: GARCH(1,1)-forecast inverse-volatility CONTINUOUS position
sizing on a buy-and-hold-long base (Moreira-Muir volatility-managed
portfolio construction).

Hypothesis (see knowledge_base/strategies_log.jsonl, this iteration):
Per https://marketmaker.cc/en/blog/post/volatility-targeting-garch-strategy/
("Volatility Targeting and Trading with GARCH Forecasts", read via
browser_exec fallback -- web_extract ddgs backend cannot extract page
content), the volatility-targeting equation is w_t = sigma_target /
sigma_hat_t (then capped), where sigma_hat_t is a one-step-ahead
volatility FORECAST (not a trailing realized-vol window). The article
cites Moreira & Muir (2017) "Volatility-Managed Portfolios": scaling
exposure by 1/sigma^2-style inverse-vol sizing raises Sharpe ratios and
compresses drawdowns because vol clusters (highly forecastable) while
returns don't, so mechanically underweighting predictably turbulent
windows avoids the fat left tail a fixed-notional position suffers during
a vol explosion.

This repo already has:
  - a BINARY GARCH(1,1) long/flat regime gate (2026-09-07-015, rejected --
    Sharpe near-miss on both equity symbols despite MDD/TC/param-sensitivity
    passing), which only ever exits ahead of high-vol regimes rather than
    continuously re-sizing.
  - many CONTINUOUS inverse-volatility-targeting overlays (2026-09-08-165
    and descendants), but ALL of those size by a trailing ROLLING REALIZED
    STD window, which only reacts to a shock once it rolls into the window
    average.

This strategy is the first to combine the two: a genuinely fitted GARCH(1,1)
conditional-variance forecast (reacts to a return shock IMMEDIATELY via the
alpha*eps_{t-1}^2 term, not lagged into a trailing window) used as the
CONTINUOUS sizing denominator (not a binary gate) on a permanently-long base
position -- i.e. this isolates whether the GARCH model's faster shock
response, when used for continuous position-managed sizing rather than a
long/flat regime switch, produces a bigger Sharpe/MDD improvement than the
already-tested realized-vol sizing family.

Signal logic
------------
- GARCH(1,1) refit via MLE (scipy.optimize.minimize, no `arch` package
  available) every `refit_every` trading days on the trailing `lookback`
  daily log returns (same fitting code as the existing binary-gate
  strategy, 2026-09-07_garch_vol_regime_gate.py).
- One-step-ahead forecast annualized conditional vol sigma_hat_t, held
  constant until the next refit.
- Continuous exposure = clip(vol_target / sigma_hat_t, 0, leverage_cap).
- A no-trade rebalance deadband (per this repo's established
  2026-09-07-026 construction) avoids churning on every tiny forecast wobble.
- Always net-long direction (this strategy tests the SIZING mechanism in
  isolation, exactly as 2026-09-08-165 did for realized-vol sizing) --
  no separate directional signal.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (continuous exposure
    in [0, leverage_cap])
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
    """Fit GARCH(1,1) via MLE; return (omega, alpha, beta, last_sigma2, last_eps)."""
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
    lookback: int = 250,
    refit_every: int = 21,
    vol_target: float = 0.15,
    leverage_cap: float = 1.5,
    deadband: float = 0.10,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series sized by
    inverse GARCH(1,1)-forecast annualized volatility."""
    df = _prep(price_df)
    close = df["close"]
    log_ret = np.log(close / close.shift(1)).fillna(0.0)
    ret_pct = (log_ret * 100).values  # scale for GARCH fitting stability

    n = len(close)
    raw_exposure = pd.Series(0.0, index=close.index, dtype=float)

    current_vol_ann = None
    for i in range(n):
        if i >= lookback and (i % refit_every == 0 or current_vol_ann is None):
            window = ret_pct[max(0, i - lookback) : i]
            if len(window) >= 30:
                omega, alpha, beta, last_sigma2, last_eps = _fit_garch11(window)
                fcast_sigma2 = omega + alpha * last_eps ** 2 + beta * last_sigma2
                current_vol_ann = np.sqrt(max(fcast_sigma2, 1e-8) * 252) / 100.0
        if current_vol_ann is not None and current_vol_ann > 1e-6:
            raw_exposure.iloc[i] = min(vol_target / current_vol_ann, leverage_cap)
        else:
            raw_exposure.iloc[i] = 0.0

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    lookback: int = 250,
    refit_every: int = 21,
    vol_target: float = 0.15,
    leverage_cap: float = 1.5,
    deadband: float = 0.10,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        lookback=lookback,
        refit_every=refit_every,
        vol_target=vol_target,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
