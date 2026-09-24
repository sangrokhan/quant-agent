"""Strategy: Hodrick-Prescott (HP) filter trend/cycle decomposition mean-reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-XXX):
The HP filter decomposes price = trend (tau) + cycle (c), where the trend
component is a smooth, optimization-derived series (minimizes deviation
from price + lambda * roughness-of-trend penalty) rather than a simple
moving average. When the cyclical component stretches far below the trend
(price is significantly "underwater" relative to its own smooth trend),
that deviation historically mean-reverts (per
https://sourcetable.com/ai-trading-strategies/fx-moving-averages-hp-filter,
"Oversold Cyclical Threshold: Define oversold as cyclical component below
-1.5 standard deviations ... historically these setups precede mean-reversion
moves"). Source article is about FX but the mechanism (statistical trend
extraction + cycle z-score mean reversion) is asset-agnostic; here applied
to equity/crypto daily closes. First HP-filter strategy in this repo
(zero prior "Hodrick-Prescott"/"HP Filter" hits in knowledge_base index).

Signal logic
------------
- Compute the HP-filtered trend tau_t over a trailing rolling window
  (hp_window bars, recomputed each step for causality -- no lookahead: at
  time t we only use price[t-hp_window+1 : t+1] to fit tau, and read the
  LAST element of that fit as tau_t, matching the source's own "end-point"
  caveat that only the newest point is usable in real time).
- Cyclical component c_t = price_t - tau_t, standardized over the last
  hp_window bars: z_t = c_t / rolling_std(c, hp_window).
- Entry (long): z_t <= -entry_z (cycle stretched oversold vs smooth trend).
- Exit: z_t >= exit_z (reverted back toward/above trend), OR after a
  max holding period of max_hold_days (avoid indefinite holds waiting for
  reversion that never comes, e.g. in a genuine downtrend).
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable params as keyword args (lambda_, hp_window, entry_z,
exit_z, max_hold_days) per RESEARCH_LOOP.md Step 5 contract.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.sparse.linalg import spsolve


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _hp_trend_full(y: np.ndarray, lamb: float) -> np.ndarray:
    """Standard two-sided HP filter over a fixed array (batch solve).

    Solves (I + lamb * D'D) tau = y where D is the second-difference
    operator, via sparse linear solve. Used inside a trailing rolling
    window below to keep the *last* point of each window's own fit
    (avoids using future data relative to that window's endpoint).
    """
    n = len(y)
    if n < 5:
        return y.astype(float).copy()
    # second-difference operator D: (n-2) x n
    d0 = np.ones(n)
    D = sparse.diags(
        [d0[:-2], -2 * d0[:-1], d0], offsets=[0, 1, 2], shape=(n - 2, n)
    )
    I = sparse.eye(n)
    A = (I + lamb * (D.T @ D)).tocsc()
    tau = spsolve(A, y)
    return np.asarray(tau)


def _rolling_hp_trend(close: pd.Series, hp_window: int, lamb: float) -> pd.Series:
    """Causal rolling HP trend: for each t, fit HP filter on the trailing
    hp_window-bar window ending at t, and keep only the endpoint value.
    This respects the source's own "end-point problem" caveat (only the
    latest point of a window's fit is usable without repeated backward
    revision) and guarantees no lookahead.
    """
    vals = close.values.astype(float)
    n = len(vals)
    out = np.full(n, np.nan)
    for t in range(hp_window - 1, n):
        window = vals[t - hp_window + 1 : t + 1]
        tau = _hp_trend_full(window, lamb)
        out[t] = tau[-1]
    return pd.Series(out, index=close.index)


def _compute_z(
    price_df: pd.DataFrame,
    hp_window: int,
    lambda_: float,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    trend = _rolling_hp_trend(close, hp_window=hp_window, lamb=lambda_)
    cycle = close - trend
    cycle_std = cycle.rolling(hp_window, min_periods=hp_window // 2).std()
    z = cycle / cycle_std.replace(0, np.nan)
    return z


def generate_signals(
    price_df: pd.DataFrame,
    hp_window: int = 60,
    lambda_: float = 1600.0,
    entry_z: float = 1.5,
    exit_z: float = 0.0,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    z = _compute_z(price_df, hp_window=hp_window, lambda_=lambda_)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(len(df)):
        zt = z.iloc[i]
        if pd.isna(zt):
            position.iloc[i] = 0
            continue
        if not in_pos:
            if zt <= -entry_z:
                in_pos = True
                hold_count = 0
        else:
            hold_count += 1
            if zt >= exit_z or hold_count >= max_hold_days:
                in_pos = False
                hold_count = 0
        position.iloc[i] = 1 if in_pos else 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    hp_window: int = 60,
    lambda_: float = 1600.0,
    entry_z: float = 1.5,
    exit_z: float = 0.0,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)
    signal = generate_signals(
        price_df,
        hp_window=hp_window,
        lambda_=lambda_,
        entry_z=entry_z,
        exit_z=exit_z,
        max_hold_days=max_hold_days,
    )
    # position held for return on day t is yesterday's signal (avoid lookahead)
    strat_ret = daily_ret * signal.shift(1).fillna(0)
    return strat_ret
