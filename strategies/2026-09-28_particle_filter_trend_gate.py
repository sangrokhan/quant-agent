"""Strategy: Bootstrap particle filter (Sequential Monte Carlo) local-trend
state estimation, trend-following entry/exit gate.

Hypothesis (source: general particle-filter/SMC methodology corroborated
via https://www.daytrading.com/particle-filtering-hft and
https://inferensys.com/glossary/quantitative-finance-and-algorithmic-trading/regime-switching-models/particle-filter,
both read via Google SERP this iteration -- the bootstrap particle filter
/ Sequential Importance Resampling (SIR) algorithm itself is a standard,
fully public Monte Carlo state-space filtering technique, Gordon, Salmond
& Smith 1993):

Models daily log-price as a hidden local-level + local-trend state-space
system:
    level_t = level_{t-1} + trend_{t-1} + w_level  (w_level ~ N(0, q_level))
    trend_t = trend_{t-1} + w_trend                 (w_trend ~ N(0, q_trend))
    obs_t   = level_t + v                           (v ~ N(0, r_obs))
Unlike a Kalman filter (already tested in this repo 8+ times, e.g.
2026-09-08-052/2026-09-17-101), a PARTICLE filter approximates the
posterior over (level, trend) with a swarm of N discrete "particles"
(random samples) rather than assuming/propagating a single Gaussian belief
analytically -- this is the standard bootstrap/SIR particle filter
(Gordon, Salmond & Smith 1993): propagate each particle through the
process model, weight by observation likelihood, resample when the
effective sample size collapses. This repo has ZERO prior "particle
filter"/"Sequential Monte Carlo" hits (Stage-1 index search this
iteration) -- genuinely distinct estimation methodology from the repo's
existing single-hypothesis Kalman-filter entries, even though both target
a similar local-trend state-space model, because SMC naturally handles the
full (non-Gaussian, potentially multimodal) posterior rather than a single
analytic Gaussian belief.

Signal logic:
- Run the bootstrap particle filter causally (no lookahead) over the daily
  log-price series, extracting the posterior MEAN of the trend state
  E[trend_t] and its cross-particle STANDARD DEVIATION (posterior
  uncertainty) at each bar.
- Long entry: E[trend_t] crosses above zero (posterior believes the local
  trend just turned positive) AND the posterior is sufficiently confident
  (std(trend_t) below `max_trend_std`, i.e. the particle swarm agrees,
  filtering out noisy/uncertain trend estimates).
- Exit: E[trend_t] crosses back below zero, posterior uncertainty spikes
  above `max_trend_std` (swarm disagreement -- a genuine new signal
  category, distinct from a simple crossover-only exit), or a
  `max_hold_days` time-stop.

Interface contract (see validation/validators.py and validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _bootstrap_particle_filter_trend(
    log_price: np.ndarray,
    n_particles: int = 500,
    q_level: float = 1e-5,
    q_trend: float = 1e-6,
    r_obs: float = 1e-4,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """Bootstrap (SIR) particle filter for a local-level+local-trend
    state-space model. Returns (trend_mean, trend_std) arrays, both
    causal -- computed using only observations up to and including each
    bar. Standard multinomial resampling triggered whenever effective
    sample size (ESS) falls below N/2, the textbook SIR default.
    """
    rng = np.random.default_rng(seed)
    n = len(log_price)

    level_p = np.full(n_particles, log_price[0])
    trend_p = np.zeros(n_particles)
    weights = np.full(n_particles, 1.0 / n_particles)

    trend_mean = np.zeros(n)
    trend_std = np.zeros(n)
    trend_mean[0] = 0.0
    trend_std[0] = 0.0

    sqrt_q_level = np.sqrt(q_level)
    sqrt_q_trend = np.sqrt(q_trend)

    for t in range(1, n):
        # Propagate (process model, with process noise).
        level_p = level_p + trend_p + rng.normal(0.0, sqrt_q_level, n_particles)
        trend_p = trend_p + rng.normal(0.0, sqrt_q_trend, n_particles)

        # Weight by observation likelihood (Gaussian observation model).
        obs = log_price[t]
        residual = obs - level_p
        log_w = -0.5 * (residual ** 2) / r_obs
        log_w -= log_w.max()  # numerical stability
        w = np.exp(log_w)
        w_sum = w.sum()
        if w_sum <= 0 or not np.isfinite(w_sum):
            weights = np.full(n_particles, 1.0 / n_particles)
        else:
            weights = w / w_sum

        # Effective sample size; resample (multinomial) if it collapses.
        ess = 1.0 / np.sum(weights ** 2)
        if ess < n_particles / 2.0:
            idx = rng.choice(n_particles, size=n_particles, replace=True, p=weights)
            level_p = level_p[idx]
            trend_p = trend_p[idx]
            weights = np.full(n_particles, 1.0 / n_particles)

        trend_mean[t] = float(np.sum(weights * trend_p))
        trend_std[t] = float(np.sqrt(max(np.sum(weights * (trend_p - trend_mean[t]) ** 2), 0.0)))

    return trend_mean, trend_std


def generate_signals(
    price_df: pd.DataFrame,
    n_particles: int = 500,
    q_level: float = 1e-5,
    q_trend: float = 1e-6,
    r_obs: float = 1e-4,
    max_trend_std: float = 0.001,
    max_hold_days: int = 40,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a {0,1}*leverage_cap long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    log_price = np.log(close).to_numpy()

    trend_mean, trend_std = _bootstrap_particle_filter_trend(
        log_price, n_particles=n_particles, q_level=q_level, q_trend=q_trend, r_obs=r_obs
    )
    trend_up = trend_mean > 0
    confident = trend_std <= max_trend_std
    fresh_up_cross = trend_up & ~np.concatenate(([False], trend_up[:-1]))

    n = len(df)
    pos = pd.Series(0.0, index=df.index)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_now = (
                not bool(trend_up[i])
                or not bool(confident[i])
                or hold_count >= max_hold_days
            )
            if exit_now:
                in_pos = False
                hold_count = 0
            else:
                pos.iloc[i] = 1.0
        if not in_pos and bool(fresh_up_cross[i]) and bool(confident[i]):
            in_pos = True
            hold_count = 0
            pos.iloc[i] = 1.0

    return pos * leverage_cap


def generate_returns(
    price_df: pd.DataFrame,
    n_particles: int = 500,
    q_level: float = 1e-5,
    q_trend: float = 1e-6,
    r_obs: float = 1e-4,
    max_trend_std: float = 0.001,
    max_hold_days: int = 40,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return the daily strategy return series (no transaction costs)."""
    df = _prep(price_df)
    pos = generate_signals(
        df,
        n_particles=n_particles,
        q_level=q_level,
        q_trend=q_trend,
        r_obs=r_obs,
        max_trend_std=max_trend_std,
        max_hold_days=max_hold_days,
        leverage_cap=leverage_cap,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0.0)
    return strat_ret
