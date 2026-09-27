"""Strategy: GJR-GARCH(1,1) asymmetric-volatility regime gate on an SMA
trend-following long baseline.

Hypothesis (source: Glosten, Jagannathan & Runkle (1993), "On the Relation
between the Expected Value and the Volatility of the Nominal Excess Return
on Stocks", Journal of Finance -- formula/concept corroborated via NYU
Stern V-Lab's public GJR-GARCH documentation
https://vlab.stern.nyu.edu/docs/volatility/GJR-GARCH, read via browser_exec
this iteration, plus general-knowledge corroboration from QuantInsti/Medium/
Dr Nicky Grant sources returned in the same Google SERP; the GJR-GARCH
functional form itself is textbook-standard and was implemented here from
first principles, distinct from this repo's existing symmetric GARCH(1,1)
entry 2026-09-07-015 and HAR-RV entry 2026-09-20-100 which do NOT model the
leverage effect):

sigma_t^2 = omega + alpha*eps_{t-1}^2 + gamma*eps_{t-1}^2*I(eps_{t-1}<0) + beta*sigma_{t-1}^2

The GJR-GARCH(1,1) extension adds a single asymmetry term (gamma) that only
activates on NEGATIVE return shocks (I(.) is an indicator function), so
negative returns increase forecast conditional volatility more than
positive returns of equal magnitude -- the well-documented equity "leverage
effect" (Black 1976, Christie 1982): a falling stock price raises a firm's
financial leverage (debt/equity), mechanically raising equity return
volatility.

This repo's existing GARCH(1,1) entry (2026-09-07-015, accepted) already
demonstrated a GARCH-forecast volatility gate works as a long/flat regime
filter on this repo's daily-bar universe. This iteration tests whether the
GJR-GARCH asymmetry term specifically improves on that baseline: by
explicitly forecasting HIGHER volatility immediately after a down day (via
the gamma term), the gate should react FASTER to genuine risk-off regime
shifts (turning flat sooner after a sharp selloff) than the symmetric
GARCH(1,1) gate, which only sees the squared magnitude of yesterday's shock
with no sign-dependence.

Model fitting: GJR-GARCH(1,1) parameters (omega, alpha, gamma, beta) are
estimated via constrained MLE (scipy.optimize.minimize, no `arch` package
available in this repo's environment, matching this repo's established
practice from strategies/2026-09-07_garch_vol_gate.py-style entries),
refit every `refit_every` bars on a trailing `lookback` window of daily
log returns to keep the fit causal (no lookahead) and computationally
tractable for a rolling backtest.

Signal logic:
- At each bar (after enough history + first fit), compute the GJR-GARCH
  one-step-ahead forecast conditional volatility (annualized).
- Long while forecast annualized vol <= `vol_threshold` (calm/normal
  regime per the model's own forecast, INCLUDING its leverage-effect
  awareness of any recent down-day shock); flat otherwise.
- No separate trend-direction signal -- this is a pure regime-timing
  overlay on being long the underlying itself (matching this repo's
  established GARCH-gate convention from 2026-09-07-015), not combined
  with a crossover trigger, to isolate whether the ASYMMETRY specifically
  (vs the already-tested symmetric GARCH gate) changes the result.

Interface contract (see validation/validators.py and validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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


def _gjr_garch_neg_loglik(params: np.ndarray, eps: np.ndarray) -> float:
    omega, alpha, gamma, beta = params
    n = len(eps)
    sigma2 = np.empty(n)
    sigma2[0] = np.var(eps)
    for t in range(1, n):
        indicator = 1.0 if eps[t - 1] < 0 else 0.0
        sigma2[t] = (
            omega
            + alpha * eps[t - 1] ** 2
            + gamma * (eps[t - 1] ** 2) * indicator
            + beta * sigma2[t - 1]
        )
        if sigma2[t] <= 1e-12:
            sigma2[t] = 1e-12
    ll = -0.5 * np.sum(np.log(2 * np.pi * sigma2) + (eps ** 2) / sigma2)
    return -ll


def _fit_gjr_garch(eps: np.ndarray) -> np.ndarray:
    """Fit GJR-GARCH(1,1) via constrained MLE. Returns [omega, alpha, gamma, beta].

    Falls back to a simple long-run-variance-only fit if optimization fails
    to converge (keeps the rolling backtest from crashing on pathological
    windows).
    """
    var0 = float(np.var(eps)) if len(eps) > 1 else 1e-4
    x0 = np.array([var0 * 0.05, 0.05, 0.05, 0.85])
    bounds = [(1e-10, None), (0.0, 1.0), (0.0, 1.0), (0.0, 0.999)]
    try:
        res = minimize(
            _gjr_garch_neg_loglik,
            x0,
            args=(eps,),
            method="L-BFGS-B",
            bounds=bounds,
            options={"maxiter": 200},
        )
        if res.success and np.all(np.isfinite(res.x)):
            omega, alpha, gamma, beta = res.x
            # Stationarity-ish sanity check (alpha + gamma/2 + beta < 1).
            if alpha + gamma / 2.0 + beta < 1.0:
                return res.x
    except Exception:  # noqa: BLE001
        pass
    return np.array([var0 * 0.05, 0.05, 0.05, 0.85])


def _gjr_garch_vol_forecast(
    close: pd.Series,
    lookback: int,
    refit_every: int,
    periods_per_year: int = 252,
) -> np.ndarray:
    """Rolling causal one-step-ahead GJR-GARCH annualized vol forecast."""
    log_ret = np.log(close / close.shift(1)).to_numpy()
    n = len(log_ret)
    out = np.full(n, np.nan)

    params = None
    for t in range(lookback, n):
        if params is None or (t - lookback) % refit_every == 0:
            window = log_ret[t - lookback : t]
            window = window[~np.isnan(window)]
            if len(window) < lookback // 2:
                continue
            params = _fit_gjr_garch(window * 100.0)  # scale for numerical stability

        window = log_ret[t - lookback : t]
        window = window[~np.isnan(window)] * 100.0
        if len(window) < 2:
            continue
        omega, alpha, gamma, beta = params
        # Recompute sigma2 path over the window to get sigma2[-1], then
        # forecast one step ahead using the most recent (scaled) shock.
        m = len(window)
        sigma2 = np.empty(m)
        sigma2[0] = np.var(window)
        for j in range(1, m):
            ind = 1.0 if window[j - 1] < 0 else 0.0
            sigma2[j] = omega + alpha * window[j - 1] ** 2 + gamma * (window[j - 1] ** 2) * ind + beta * sigma2[j - 1]
            if sigma2[j] <= 1e-12:
                sigma2[j] = 1e-12
        last_eps = window[-1]
        ind_last = 1.0 if last_eps < 0 else 0.0
        forecast_sigma2 = omega + alpha * last_eps ** 2 + gamma * (last_eps ** 2) * ind_last + beta * sigma2[-1]
        # Undo the *100 scaling (variance scales by 100^2) then annualize.
        daily_vol = np.sqrt(max(forecast_sigma2, 1e-12)) / 100.0
        out[t] = daily_vol * np.sqrt(periods_per_year)

    return out


def generate_signals(
    price_df: pd.DataFrame,
    lookback: int = 250,
    refit_every: int = 20,
    vol_threshold: float = 0.25,
    trend_window: int = 0,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a {0,1}*leverage_cap long/flat position series.

    ``trend_window`` (0 = disabled) optionally ANDs the GJR-GARCH calm-vol
    gate with a plain close > SMA(trend_window) trend filter -- a pure
    volatility-regime gate with no trend-direction awareness can stay long
    through a low-volatility grind DOWN (e.g. a slow bear market), which
    inflates drawdown; requiring the trend filter too keeps the strategy
    out of calm-but-declining regimes. ``leverage_cap`` scales the {0,1}
    position down uniformly (this repo's standard crypto MDD-control
    retune knob).
    """
    df = _prep(price_df)
    close = df["close"]

    vol_forecast = _gjr_garch_vol_forecast(close, lookback=lookback, refit_every=refit_every)
    calm = pd.Series(vol_forecast, index=df.index) <= vol_threshold
    calm = calm.fillna(False)

    if trend_window and trend_window > 0:
        sma = close.rolling(trend_window).mean()
        trend_ok = (close > sma).fillna(False)
        calm = calm & trend_ok

    return calm.astype(float) * leverage_cap


def generate_returns(
    price_df: pd.DataFrame,
    lookback: int = 250,
    refit_every: int = 20,
    vol_threshold: float = 0.25,
    trend_window: int = 0,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return the daily strategy return series (no transaction costs)."""
    df = _prep(price_df)
    pos = generate_signals(
        df,
        lookback=lookback,
        refit_every=refit_every,
        vol_threshold=vol_threshold,
        trend_window=trend_window,
        leverage_cap=leverage_cap,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0.0)
    return strat_ret
