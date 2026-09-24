"""Strategy: OU half-life-gated Z-score mean reversion with a DYNAMIC
per-trade time-stop of 3x the currently-fitted half-life (not a fixed
constant), plus z-proportional position sizing capped near |z|=3.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-XXX):
Per HMA Quant's "Mean Reversion and the Ornstein-Uhlenbeck Process: Trading
Half-Lives" (https://hmaquant.substack.com/p/mean-reversion-and-the-ornstein-uhlenbeck,
read this iteration -- web_search worked normally for the initial query),
the source's own explicit rule set for trading an OU-fitted spread is:
  1. Enter against the dislocation when |z| >= 2.
  2. Size PROPORTIONAL to z, capped near z=3 (so a 2.5-sigma dislocation
     carries only 25% more risk than a 2-sigma one, not unboundedly more).
  3. Exit when |z| falls below about 0.5 (not all the way to 0 -- "the last
     few tenths of a sigma decay slowly and pay little").
  4. "The most underused tool in stat arb": a hard TIME STOP at THREE
     half-lives -- by then only 12.5% of the expected dislocation should
     remain under the fitted model; a position that hasn't converged by
     then is "not early, it's broken. Cut it."

This repo already has THREE prior OU half-life attempts, all rejected/
near-miss (2026-09-07-012 binary w/ FIXED max_hold_days=20 constant and
exit_z=0; 2026-09-12-157 z-smoothing fix, made it worse; 2026-09-17-070
continuous tanh-sizing dial, decisively worse full-sample). None of them
used a half-life-PROPORTIONAL dynamic time stop (they all used an arbitrary
fixed max_hold_days or full mean-reversion-to-zero exit) or the source's
specific z>=2 entry / |z|<0.5 exit / z-proportional-capped-at-3 sizing
rules. This iteration implements those exact rules for the first time in
this repo, using the identical AR(1)/half-life fit already confirmed
correct in the prior 3 entries (same formula, so no re-derivation risk),
testing whether the SPECIFIC rule set from a dedicated OU-trading source
(rather than this repo's own earlier ad hoc choices) is what was missing.

Signal logic
------------
- Rolling OLS AR(1) on log(close) (identical formula to prior OU entries):
  b = Cov(X_lag, dX)/Var(X_lag); theta = -ln(1+b); half_life = ln(2)/theta;
  mu = -a/b; sigma_eq = sigma_resid*sqrt(1/(2*theta)); z = (X-mu)/sigma_eq.
- Regime gate: tradable only when b < 0 AND min_halflife <= half_life <=
  max_halflife (same sweet-spot rule as prior entries).
- Entry (long, mean-reversion from below): tradable AND z <= -entry_z
  (default entry_z=2.0, source's own threshold).
- Sizing: exposure = base_exposure + sensitivity * clip(-z, 0, z_cap) / z_cap
  (z-proportional, capped at z_cap=3.0 per source's explicit risk-control
  rule -- NOT unbounded, NOT purely binary).
- Exit: |z| < exit_z (default 0.5, source's own "pay little past this"
  level) OR regime breaks OR bars-held >= time_stop_multiple * half_life
  at entry (dynamic per-trade time stop, default 3x half-life, per source's
  explicit "three half-lives" rule -- this is the key novel mechanism vs.
  prior entries' fixed max_hold_days constant).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (position/exposure)
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


def _ou_fit(close: pd.Series, lookback: int):
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

    return X, b, theta, half_life, z


def generate_signals(
    price_df: pd.DataFrame,
    lookback: int = 60,
    entry_z: float = 2.0,
    exit_z: float = 0.5,
    z_cap: float = 3.0,
    min_halflife: float = 5.0,
    max_halflife: float = 30.0,
    time_stop_multiple: float = 3.0,
    base_exposure: float = 0.2,
    sensitivity: float = 0.8,
) -> pd.Series:
    """Return a continuous [0, base_exposure+sensitivity] exposure series."""
    df = _prep(price_df)
    close = df["close"]
    X, b, theta, half_life, z = _ou_fit(close, lookback)

    tradable = (
        (b < 0)
        & (half_life >= min_halflife)
        & (half_life <= max_halflife)
        & theta.replace([np.inf, -np.inf], np.nan).notna()
        & z.notna()
    )

    entry_trigger = tradable & (z <= -entry_z)

    n = len(close)
    tradable_np = tradable.to_numpy()
    entry_np = entry_trigger.to_numpy()
    z_np = z.fillna(0.0).to_numpy()
    hl_np = half_life.fillna(0.0).to_numpy()

    exposure = np.zeros(n)
    in_position = False
    entry_idx = 0
    entry_time_stop_bars = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            regime_break = not bool(tradable_np[i])
            mean_reverted = abs(z_np[i]) < exit_z
            time_stop_hit = held >= entry_time_stop_bars
            if regime_break or mean_reverted or time_stop_hit:
                in_position = False
                exposure[i] = 0.0
                continue
            dial = min(max(-z_np[i], 0.0), z_cap) / z_cap
            exposure[i] = base_exposure + sensitivity * dial
        else:
            if bool(entry_np[i]):
                in_position = True
                entry_idx = i
                # Dynamic time stop: 3x the half-life FITTED AT ENTRY,
                # clamped to a sane minimum of a few bars.
                entry_time_stop_bars = max(int(round(time_stop_multiple * hl_np[i])), 3)
                dial = min(max(-z_np[i], 0.0), z_cap) / z_cap
                exposure[i] = base_exposure + sensitivity * dial
            else:
                exposure[i] = 0.0

    return pd.Series(exposure, index=close.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
