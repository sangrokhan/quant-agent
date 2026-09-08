"""Strategy: Firefly Oscillator midline crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-058):
LuxAlgo's Firefly Oscillator (per https://www.luxalgo.com/library/indicator/
firefly-oscillator/, browser_exec fallback -- web_search DDGS backend
returned no results for several direct query phrasings this iteration)
converts a weighted price (typical price that double-counts the close,
(H+L+2C)/4) into a z-score against its own rolling EMA basis and standard
deviation, double-smooths that z-score with a zero-lag EMA pass, and
rescales to a 0-100 range where 50 is neutral. Per the source's own trading
guide, a cross of the midline (50) flips the volatility-adjusted stretch
from bearish to bullish (or vice versa) and is the primary directional
signal; pushes beyond 80/20 mark statistically stretched (overbought/
oversold) readings. First Firefly Oscillator strategy in this repo --
distinct from every prior z-score/CCI/RSI/Stochastic-family oscillator via
its specific "weighted-price z-score, then zero-lag-smoothed, then rescaled
0-100" construction.

Signal logic
------------
- weighted_price (WP) = (High + Low + 2*Close) / 4
- basis = EMA(WP, basis_length); dev = rolling stdev(WP, basis_length)
- z = (WP - basis) / dev
- Zero-lag double smoothing (Ehlers/Mulloy-style): e1 = EMA(z, smooth_len),
  e2 = EMA(e1, smooth_len), zl = e1 + (e1 - e2)
- Rescale zl to a 0-100 firefly value via a fixed sigmoid-style squashing
  (50 + 10*zl, clipped to [0,100] -- the source doesn't publish its exact
  rescale constant, so we use a a common z-score-to-0-100 convention that
  keeps most z in [-3,3] mapped to roughly [20,80], letting the midline-
  cross rule still fire naturally on genuine regime changes).
- Entry (long): firefly crosses above 50 (midline cross, source's primary
  bullish signal).
- Exit: firefly crosses back below 50, or a max_hold_days time-stop.
- Flat (no position) whenever not in an active long.

Interface contract for validators/grid_test (see RESEARCH_LOOP.md Step 5/6):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
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


def _firefly(
    df: pd.DataFrame,
    basis_length: int = 10,
    smooth_length: int = 3,
) -> pd.Series:
    wp = (df["high"] + df["low"] + 2 * df["close"]) / 4.0

    basis = wp.ewm(span=basis_length, adjust=False).mean()
    dev = wp.rolling(basis_length).std()
    z = (wp - basis) / dev.replace(0, np.nan)

    e1 = z.ewm(span=smooth_length, adjust=False).mean()
    e2 = e1.ewm(span=smooth_length, adjust=False).mean()
    zl = e1 + (e1 - e2)

    firefly = (50 + 10 * zl).clip(lower=0, upper=100)
    return firefly


def generate_signals(
    price_df: pd.DataFrame,
    basis_length: int = 10,
    smooth_length: int = 3,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    firefly = _firefly(df, basis_length=basis_length, smooth_length=smooth_length)

    cross_up = (firefly > 50) & (firefly.shift(1) <= 50)
    cross_down = (firefly < 50) & (firefly.shift(1) >= 50)

    cross_up_arr = cross_up.to_numpy()
    cross_down_arr = cross_down.to_numpy()
    pos_arr = np.zeros(len(df), dtype=int)

    in_pos = False
    entry_idx = -1
    for i in range(len(df)):
        if in_pos:
            held = i - entry_idx
            if cross_down_arr[i] or held >= max_hold_days:
                in_pos = False
            else:
                pos_arr[i] = 1
        if not in_pos and cross_up_arr[i]:
            in_pos = True
            entry_idx = i
            pos_arr[i] = 1

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    basis_length: int = 10,
    smooth_length: int = 3,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        basis_length=basis_length,
        smooth_length=smooth_length,
        max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change()
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns = strat_returns.fillna(0.0)
    return strat_returns
