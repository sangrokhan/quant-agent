"""Strategy: Ornstein-Uhlenbeck (OU) half-life-gated Z-score as a CONTINUOUS
SIZING dial (not a binary entry/exit trigger), leverage-cap-aware for crypto.

Hypothesis (this cron trigger's iteration 1):
Per this repo's own already-confirmed OU/AR(1) half-life formula (from
strategies/2026-09-07_ou_halflife_zscore_meanrev.py, itself sourced from
https://quanterlab.com/articles/stochastic-ou-process; z-score smoothing fix
also already tried in strategies/2026-09-12_ou_halflife_zscore_smoothed_fix.py)
and reconfirmed this iteration via https://algodrill.app/mean-reversion-strategy
("Position scaling improves on binary entry: scaling position size linearly
with the z-score ... produces smoother equity curves than a binary in/out
signal ... approximates the OU strategy's optimal policy under Gaussian
assumptions" -- AlgoDrill Module 8, "Six Points of Nuance" #3), this
iteration replaces the repo's existing OU half-life strategies' binary
{0,1} position with a CONTINUOUS exposure dial: the OU z-score
(same fitted mu/sigma_eq construction, tradable only when half-life is in
the 5-30 bar sweet spot per the source's own rule of thumb) is tanh-squashed
and used as a sizing multiplier, held via a no-trade deadband, distinct from
BOTH prior OU entries in this repo (2026-09-07-012 binary entry/exit,
2026-09-12-157 z-smoothing fix, both rejected/near-miss on parameter
sensitivity at the binary-trigger level). This is the standard "continuous
sizing dial" rescue pattern validated extensively elsewhere in this repo
(e.g. Fisher Transform, KST, Chaikin Oscillator, Twiggs Money Flow) applied
here for the first time to the OU half-life family.

Signal logic
------------
- Rolling OLS AR(1) on log(close): b = Cov(X_lag, dX) / Var(X_lag) over
  `lookback` window; a = mean(dX) - b*mean(X_lag). theta = -ln(1+b);
  half_life = ln(2)/theta. mu = -a/b; sigma_eq = sigma_resid*sqrt(1/(2*theta)).
- z = (X - mu) / sigma_eq (negative z = price below OU equilibrium = cheap).
- Regime gate: tradable only when b < 0 AND min_halflife <= half_life <=
  max_halflife (source's own rule of thumb for a genuinely tradable, not
  noise-dominated or non-mean-reverting, series).
- Sizing dial: dial = tanh(-z) when tradable else 0 (long-only mean
  reversion: dial rises as price falls below equilibrium). Held via a
  no-trade deadband to cut turnover.
- exposure = clip(base_exposure + sensitivity * dial, 0, leverage_cap).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap])
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
    raw = raw_exposure.fillna(0.0).to_numpy()
    held = np.zeros_like(raw)
    current = 0.0
    for i, r in enumerate(raw):
        if abs(r - current) > deadband:
            current = r
        held[i] = current
    return pd.Series(held, index=raw_exposure.index)


def _ou_z_and_regime(close: pd.Series, lookback: int, min_halflife: float, max_halflife: float):
    X = np.log(close.clip(lower=1e-9))
    dX = X.diff()
    X_lag = X.shift(1)

    roll_cov = X_lag.rolling(lookback).cov(dX)
    roll_var = X_lag.rolling(lookback).var()
    b = roll_cov / roll_var
    a = dX.rolling(lookback).mean() - b * X_lag.rolling(lookback).mean()

    pred = a + b * X_lag
    resid = dX - pred
    sigma_resid = resid.rolling(lookback).std()

    with np.errstate(invalid="ignore", divide="ignore"):
        theta = -np.log1p(b)
        half_life = np.log(2) / theta
        mu = -a / b
        sigma_eq = sigma_resid * np.sqrt(1.0 / (2.0 * theta))
        z = (X - mu) / sigma_eq

    tradable = (
        (b < 0)
        & (half_life >= min_halflife)
        & (half_life <= max_halflife)
        & theta.replace([np.inf, -np.inf], np.nan).notna()
        & z.notna()
    )
    return z, tradable


def generate_signals(
    price_df: pd.DataFrame,
    lookback: int = 60,
    min_halflife: float = 5.0,
    max_halflife: float = 30.0,
    base_exposure: float = 0.3,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    z, tradable = _ou_z_and_regime(close, lookback, min_halflife, max_halflife)
    dial = np.tanh((-z).fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(tradable.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    lookback: int = 60,
    min_halflife: float = 5.0,
    max_halflife: float = 30.0,
    base_exposure: float = 0.3,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        lookback=lookback,
        min_halflife=min_halflife,
        max_halflife=max_halflife,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
