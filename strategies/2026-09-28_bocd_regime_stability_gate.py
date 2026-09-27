"""Strategy: Bayesian Online Changepoint Detection (BOCD, Adams & MacKay
2007) run-length regime-stability gate on an SMA trend-following entry.

Hypothesis (source: Adams, R.P. & MacKay, D.J.C. (2007), "Bayesian Online
Changepoint Detection", arXiv:0710.3742; algorithm walkthrough corroborated
via Gregory Gundersen's detailed derivation
https://gregorygundersen.com/blog/2019/08/13/bocd/, read this iteration via
browser_exec):

BOCD models the time since the last "changepoint" (structural break in the
data-generating distribution) as a latent "run length" r_t, recursively
updated via exact Bayesian message-passing:
- p(r_t=0 | x_1:t)  proportional to  sum_l p(x_t | r_{t-1}=l) * H(l+1) * p(r_{t-1}=l | x_1:t-1)   [changepoint just occurred]
- p(r_t=l+1 | x_1:t) proportional to  p(x_t | r_{t-1}=l) * (1-H(l+1)) * p(r_{t-1}=l | x_1:t-1)     [run continues]
where H(.) is a constant hazard rate (1/lambda, geometric prior on
changepoint spacing) and p(x_t | r_{t-1}=l) is the "underlying predictive
model" (UPM) -- here a Normal-Gamma conjugate model on the daily log-return
series (unknown mean AND variance, standard Bayesian-Gaussian conjugate
updating), giving a closed-form Student-t predictive density at each step
(exactly as in Adams & MacKay's own worked example).

This repo has one prior CHANGEPOINT-adjacent entry (2026-09-22-002) that
used a SIMPLIFIED variance-ratio z-score PROXY for changepoint detection,
not the actual BOCD recursive Bayesian algorithm -- zero prior hits for
"BOCD"/"Bayesian Online Changepoint Detection" specifically in this repo's
knowledge base. This iteration implements the real recursive run-length
posterior from scratch (numpy, no external changepoint library).

Signal logic:
- At each bar, run the BOCD recursion on the trailing daily log-return
  series (causal -- only uses returns up to and including that bar) and
  extract the run-length posterior's EXPECTED value E[r_t] (a continuous
  "how long has the current regime been stable" measure, more informative
  than just the single most-likely run length).
- Entry gate: a plain SMA(fast) > SMA(slow) trend-following crossover is
  only allowed to trigger a fresh entry when E[r_t] >= `min_run_length`
  (the model itself judges the current regime as sufficiently established/
  stable, not fresh off a just-detected changepoint where the underlying
  distribution is still highly uncertain).
- Exit: trend crossover reversing, a FRESH high-confidence changepoint
  detected while long (P(r_t=0) exceeding `changepoint_prob_threshold`,
  i.e. the model believes a NEW regime just started, a natural defensive
  exit distinct from the entry gate), or a max_hold_days time-stop.

Interface contract (see validation/validators.py and validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import gammaln


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _studentpdf(x: np.ndarray, df: np.ndarray, loc: np.ndarray, scale: np.ndarray) -> np.ndarray:
    """Vectorized Student-t density, Adams & MacKay's own predictive form."""
    scale = np.maximum(scale, 1e-12)
    z = (x - loc) / scale
    log_pdf = (
        gammaln((df + 1) / 2.0)
        - gammaln(df / 2.0)
        - 0.5 * np.log(df * np.pi)
        - np.log(scale)
        - ((df + 1) / 2.0) * np.log1p((z ** 2) / df)
    )
    return np.exp(log_pdf)


def _bocd_run_length_stats(
    returns: np.ndarray,
    hazard_lambda: float = 100.0,
    mu0: float = 0.0,
    kappa0: float = 1.0,
    alpha0: float = 1.0,
    beta0: float = 1e-4,
    max_run_cap: int = 500,
) -> tuple[np.ndarray, np.ndarray]:
    """Adams & MacKay (2007) exact BOCD recursion with a Normal-Gamma UPM.

    Returns (expected_run_length, p_changepoint) arrays aligned with
    ``returns``. ``max_run_cap`` truncates the run-length distribution's
    tail (run lengths beyond this are dropped, standard practical BOCD
    approximation -- their probability mass is negligible for
    stationary-ish financial return series with a sane hazard rate) to
    keep the O(t) per-bar cost from growing unbounded across a long
    backtest.
    """
    n = len(returns)
    H = 1.0 / hazard_lambda

    R = np.array([1.0])  # p(r_0=0)=1
    muT = np.array([mu0])
    kappaT = np.array([kappa0])
    alphaT = np.array([alpha0])
    betaT = np.array([beta0])

    expected_rl = np.zeros(n)
    p_cp = np.zeros(n)

    for t in range(n):
        x = returns[t]

        pred_scale = np.sqrt(betaT * (kappaT + 1.0) / (alphaT * kappaT))
        pred_df = 2.0 * alphaT
        pred_probs = _studentpdf(x, pred_df, muT, pred_scale)

        growth_probs = R * pred_probs * (1.0 - H)
        cp_prob = np.sum(R * pred_probs * H)

        new_R = np.concatenate(([cp_prob], growth_probs))
        total = new_R.sum()
        if total <= 0 or not np.isfinite(total):
            new_R = np.zeros_like(new_R)
            new_R[0] = 1.0
        else:
            new_R = new_R / total

        # Bayesian update of Normal-Gamma sufficient statistics per run length.
        new_muT = np.concatenate(([mu0], (kappaT * muT + x) / (kappaT + 1.0)))
        new_kappaT = np.concatenate(([kappa0], kappaT + 1.0))
        new_alphaT = np.concatenate(([alpha0], alphaT + 0.5))
        new_betaT = np.concatenate(
            ([beta0], betaT + (kappaT * (x - muT) ** 2) / (2.0 * (kappaT + 1.0)))
        )

        if len(new_R) > max_run_cap:
            new_R = new_R[:max_run_cap]
            new_R = new_R / new_R.sum()
            new_muT = new_muT[:max_run_cap]
            new_kappaT = new_kappaT[:max_run_cap]
            new_alphaT = new_alphaT[:max_run_cap]
            new_betaT = new_betaT[:max_run_cap]

        R, muT, kappaT, alphaT, betaT = new_R, new_muT, new_kappaT, new_alphaT, new_betaT

        run_lengths = np.arange(len(R))
        expected_rl[t] = float(np.sum(run_lengths * R))
        p_cp[t] = float(R[0])

    return expected_rl, p_cp


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 20,
    slow_window: int = 50,
    hazard_lambda: float = 100.0,
    min_run_length: int = 15,
    changepoint_prob_threshold: float = 0.3,
    max_hold_days: int = 40,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a {0,1}*leverage_cap long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    log_ret = np.log(close / close.shift(1)).fillna(0.0).to_numpy()

    expected_rl, p_cp = _bocd_run_length_stats(log_ret, hazard_lambda=hazard_lambda)
    expected_rl_s = pd.Series(expected_rl, index=df.index)
    p_cp_s = pd.Series(p_cp, index=df.index)

    fast = close.rolling(fast_window).mean()
    slow = close.rolling(slow_window).mean()
    trend_up = (fast > slow).fillna(False)
    fresh_up_cross = trend_up & (~trend_up.shift(1).fillna(False))

    stable_regime = (expected_rl_s >= min_run_length).fillna(False)
    fresh_cp = (p_cp_s >= changepoint_prob_threshold).fillna(False)

    trend_up_arr = trend_up.to_numpy()
    fresh_up_cross_arr = fresh_up_cross.to_numpy()
    stable_arr = stable_regime.to_numpy()
    fresh_cp_arr = fresh_cp.to_numpy()

    n = len(df)
    pos = pd.Series(0.0, index=df.index)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_now = (
                not bool(trend_up_arr[i])
                or bool(fresh_cp_arr[i])
                or hold_count >= max_hold_days
            )
            if exit_now:
                in_pos = False
                hold_count = 0
            else:
                pos.iloc[i] = 1.0
        if not in_pos and bool(fresh_up_cross_arr[i]) and bool(stable_arr[i]):
            in_pos = True
            hold_count = 0
            pos.iloc[i] = 1.0

    return pos * leverage_cap


def generate_returns(
    price_df: pd.DataFrame,
    fast_window: int = 20,
    slow_window: int = 50,
    hazard_lambda: float = 100.0,
    min_run_length: int = 15,
    changepoint_prob_threshold: float = 0.3,
    max_hold_days: int = 40,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return the daily strategy return series (no transaction costs)."""
    df = _prep(price_df)
    pos = generate_signals(
        df,
        fast_window=fast_window,
        slow_window=slow_window,
        hazard_lambda=hazard_lambda,
        min_run_length=min_run_length,
        changepoint_prob_threshold=changepoint_prob_threshold,
        max_hold_days=max_hold_days,
        leverage_cap=leverage_cap,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0.0)
    return strat_ret
