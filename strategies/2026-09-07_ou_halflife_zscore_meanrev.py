"""Strategy: Ornstein-Uhlenbeck (OU) half-life-gated Z-score mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-012):
Per QuanterLab's OU-process article
(https://quanterlab.com/articles/stochastic-ou-process): fit a discrete-time
AR(1) to price over a rolling lookback window,
    X(t) - X(t-1) = a + b * X(t-1) + eps(t)
giving mean-reversion speed theta = -ln(1+b)/dt, implied long-run mean
mu = -a/b, half-life = -ln(2)/ln(1+b), and equilibrium std
sigma_eq = sigma_resid * sqrt(1/(2*theta)). Trade signal: z = (X - mu) /
sigma_eq; long when z < -entry_z, exit when z crosses back above -exit_z.
Per the source's own "half-life rules of thumb", only trade when the FITTED
half-life falls in the 5-30 bar "tradable mean reversion" sweet spot (too
fast = noise/microstructure, not a tradable edge; too slow/negative = not
actually mean-reverting -- "walk away"). This differs fundamentally from the
already-tested zscore_meanrev strategies in this repo, which use a simple
rolling mean/std z-score with no fitted reversion-speed (theta) gate at
all -- here the OU half-life filter is the core novel mechanism, not just
another z-score threshold variant.

Signal logic
------------
- Rolling OLS on log(close): b = Cov(X_lag, dX) / Var(X_lag) over
  `lookback` window (dt=1 bar); a = mean(dX) - b*mean(X_lag).
- theta = -ln(1+b); half_life = ln(2) / theta (in bars).
- Regime gate: only tradable when b < 0 (mean-reverting slope) AND
  min_halflife <= half_life <= max_halflife.
- mu = -a / b (implied long-run mean); sigma_resid = rolling std of
  regression residuals (dX - a - b*X_lag); sigma_eq = sigma_resid *
  sqrt(1 / (2*theta)).
- z = (X - mu) / sigma_eq.
- Entry (long): regime gate active AND z < -entry_z.
- Exit: z >= -exit_z (reverted back toward/past the mean), OR regime gate
  turns off (half-life leaves the tradable window), OR max_hold_days.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
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


def generate_signals(
    price_df: pd.DataFrame,
    lookback: int = 60,
    entry_z: float = 1.5,
    exit_z: float = 0.0,
    min_halflife: float = 5.0,
    max_halflife: float = 30.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
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
    entry = tradable & (z < -entry_z)
    exit_meanrev = z >= -exit_z

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            exit_hit = bool(exit_meanrev.iloc[i]) if not pd.isna(exit_meanrev.iloc[i]) else True
            regime_break = not bool(tradable.iloc[i]) if not pd.isna(tradable.iloc[i]) else True
            if exit_hit or regime_break or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            entry_hit = bool(entry.iloc[i]) if not pd.isna(entry.iloc[i]) else False
            if entry_hit:
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
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
