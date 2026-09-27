"""Strategy: CARR(1,1) range-based volatility regime gate + SMA trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per Chou (2005), "Forecasting Financial Volatilities with Extreme Values:
The Conditional Autoregressive Range (CARR) Model" (formula reviewed via
Ratnayake & Samaranayake's TACARR paper, arXiv:2202.03351 Section 2.1, read
via direct PDF text extraction after web_extract's ddgs backend and the
browser's native PDF viewer could not extract arxiv's rendered text).
Genuinely novel for this repo (0 prior "CARR" hits): CARR is structurally
identical to GARCH(1,1) -- same recursive conditional-expectation-of-a-
non-negative-process form -- but models the daily HIGH-LOW LOG-PRICE RANGE
R_t = P_t^high - P_t^low instead of squared/absolute RETURNS:

    R_t = lambda_t * eps_t,   eps_t iid, non-negative support, E[eps_t]=1
    lambda_t = omega + alpha * R_{t-1} + beta * lambda_{t-1}   (CARR(1,1))

Chou's own empirical finding (cited in the TACARR paper): CARR forecasts
volatility more efficiently than return-based GARCH because the intraday
high-low range is a more information-rich (lower-noise) volatility proxy
than squared close-to-close returns (per Parkinson 1980/Alizadeh-Brandt-
Diebold 2002, also cited in the source). This iteration applies this same
cron trigger's own repeatedly-validated trend-filter AND-gate pattern
(already confirmed 4x this trigger on symmetric GARCH, GJR-GARCH, EGARCH,
and HAR-D -- see 2026-09-28-022/024/025/026): a CARR-implied calm-volatility
gate (fitted lambda_t below a threshold, i.e. a QUIET expected range) ANDed
with a plain close > SMA(trend_window) trend filter, since this repo's own
empirical lesson (recorded 4x this trigger) is that a pure vol-regime gate
without an explicit directional filter systematically fails, regardless of
which conditional-variance/range model produces the gate.

CARR(1,1) MLE fit (data/loaders.py's OHLCV frame already provides high/low
columns -- no new data source needed): the {eps_t} disturbance density is
assumed EXPONENTIAL with unit mean (Chou's original ACD/CARR baseline
specification, the simplest and most commonly cited variant -- eps_t ~
Exp(1)), giving a closed-form negative log-likelihood
-sum(log(1/lambda_t) - R_t/lambda_t) to minimize via `scipy.optimize.minimize`
on (omega, alpha, beta), fit ONCE on the full available price history
(same single-fit-then-apply convention as this repo's other from-scratch
volatility-model entries, e.g. GARCH/GJR-GARCH/EGARCH this same trigger).

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


def _carr_lambda(range_series: pd.Series) -> pd.Series:
    """Fit a CARR(1,1) model (exponential disturbance, unit mean) via MLE
    on the full range series, returning the fitted conditional expected
    range lambda_t at every bar (in-sample fit, applied to compute a
    regime gate -- consistent with this repo's other from-scratch
    volatility-model strategies' single full-sample-fit convention)."""
    r = range_series.to_numpy()
    r = np.where(np.isfinite(r) & (r > 0), r, np.nan)
    valid_mean = np.nanmean(r)
    r_filled = np.where(np.isfinite(r), r, valid_mean)

    n = len(r_filled)

    def neg_log_lik(params):
        omega, alpha, beta = params
        if omega <= 0 or alpha < 0 or beta < 0 or alpha + beta >= 1:
            return 1e10
        lam = np.empty(n)
        lam[0] = valid_mean
        for t in range(1, n):
            lam[t] = omega + alpha * r_filled[t - 1] + beta * lam[t - 1]
        lam = np.clip(lam, 1e-8, None)
        # Exponential(mean=lam) log-density: -log(lam) - r/lam
        ll = -np.log(lam) - r_filled / lam
        return -np.sum(ll)

    x0 = [valid_mean * 0.05, 0.1, 0.8]
    try:
        res = minimize(neg_log_lik, x0, method="Nelder-Mead",
                        options={"maxiter": 2000, "xatol": 1e-6, "fatol": 1e-6})
        omega, alpha, beta = res.x
        if omega <= 0 or alpha < 0 or beta < 0 or alpha + beta >= 1:
            omega, alpha, beta = valid_mean * 0.05, 0.1, 0.8
    except Exception:
        omega, alpha, beta = valid_mean * 0.05, 0.1, 0.8

    lam = np.empty(n)
    lam[0] = valid_mean
    for t in range(1, n):
        lam[t] = omega + alpha * r_filled[t - 1] + beta * lam[t - 1]

    return pd.Series(lam, index=range_series.index)


def _compute_signal_frame(
    price_df: pd.DataFrame,
    trend_window: int,
) -> pd.DataFrame:
    df = _prep(price_df)
    log_high = np.log(df["high"].replace(0, np.nan))
    log_low = np.log(df["low"].replace(0, np.nan))
    range_series = (log_high - log_low).clip(lower=1e-8)

    lam = _carr_lambda(range_series)
    # Shift by 1: today's regime gate uses YESTERDAY's fitted lambda (the
    # forecast made at the close of t-1 for period t), no look-ahead.
    lam_shifted = lam.shift(1)

    sma = df["close"].rolling(trend_window).mean()
    trend_up = df["close"] > sma

    out = pd.DataFrame({"lambda": lam_shifted, "trend_up": trend_up}, index=df.index)
    return out


def generate_signals(
    price_df: pd.DataFrame,
    vol_threshold_quantile: float = 0.5,
    trend_window: int = 100,
    min_hold_days: int = 10,
) -> pd.Series:
    """Return a 0/1 long/flat position series. Long when the CARR-implied
    expected range lambda_t is below its own historical
    `vol_threshold_quantile` (a "calm" expected-range regime) AND
    close > SMA(trend_window) (uptrend confirmation) -- the AND-gate fix
    this repo has now validated 4x this cron trigger on GARCH-family
    variance regime gates. `min_hold_days` enforces a minimum holding
    period once a position is entered, to reduce whipsaw-driven trade
    frequency (a common fix in this repo's other range/regime-gate
    strategies, e.g. the SMA-window tuning noted in 2026-09-28-027's grid
    finding)."""
    df = _prep(price_df)
    sig = _compute_signal_frame(df, trend_window)
    lam = sig["lambda"]
    trend_up = sig["trend_up"]

    threshold = lam.quantile(vol_threshold_quantile)
    calm = lam < threshold

    raw_signal = (calm & trend_up).fillna(False).to_numpy()
    n = len(raw_signal)
    pos_vals = np.zeros(n, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            if not raw_signal[i] and hold_count >= min_hold_days:
                in_pos = False
                pos_vals[i] = 0
            else:
                pos_vals[i] = 1
        else:
            if raw_signal[i]:
                in_pos = True
                hold_count = 0
                pos_vals[i] = 1
            else:
                pos_vals[i] = 0
    return pd.Series(pos_vals, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    vol_threshold_quantile: float = 0.5,
    trend_window: int = 100,
    min_hold_days: int = 10,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df, vol_threshold_quantile=vol_threshold_quantile, trend_window=trend_window,
        min_hold_days=min_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
