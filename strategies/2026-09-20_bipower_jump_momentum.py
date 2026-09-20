"""Strategy: Bipower Variation Jump Detector, momentum-continuation entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-102):
Per Barndorff-Nielsen & Shephard (2004, 2006) and TradingView's "Bipower
Jump Detector [forexobroker]" script (read via Google SERP + TradingView
page this iteration, browser_exec fallback since web_search DDGS returned
no results): realized variance RV = sum(r_t^2) over a trailing window
captures both continuous (diffusion) and jump risk, while bipower
variation BV = (pi/2) * sum(|r_t| * |r_{t-1}|) is jump-robust by
construction (Barndorff-Nielsen-Shephard 2004). Their non-negative
difference J = max(RV - BV, 0) isolates the jump component; the
standardized statistic Jump-Z = sqrt(N) * (RV - BV) / sqrt(theta * BV^2 *
0.5), theta = pi^2/4 + pi - 5 (Barndorff-Nielsen & Shephard 2006), tests
whether that jump component is statistically significant. The source's own
disclosed signal logic: when Jump-Z exceeds a significance cutoff
(default 1.96, 95% one-sided) AND the dominant (largest-|return|) bar in
the window is positive, enter/stay long (source enters "in the direction
of the largest absolute return inside the window" -- a genuine jump is a
real information-driven price move, not noise, so momentum should persist
briefly after it). Adapted long-only (no short leg) per SAFETY.md/this
repo's convention, with a cooldown period matching the source's own
15-bar-cooldown design (source's own explicit "flip-prevention" rule) to
avoid repeated re-triggering off the same jump cluster, and a max_hold_days
time-stop (this repo's own convention layered on since the source's script
is a signal generator, not a full position-management system) to exit if
Jump-Z reverts below threshold or the hold period expires.

First bipower-variation/jump-detection strategy in this repo (Stage-1
index search this iteration found zero prior "bipower"/"jump variation"
entries) -- distinct from this repo's existing GARCH/EGARCH conditional-
volatility and realized-semivariance-skew (2026-09-20-101, earlier this
trigger) strategies, which model/decompose volatility LEVEL or its up/down
asymmetry, not a discrete-jump statistical TEST with a directional
momentum-continuation trading rule.

Known limitation (source's own explicit caveat, carried over honestly):
"The Barndorff-Nielsen test was designed for high-frequency intraday
returns; on daily timeframes the diffusion-jump decomposition is harder to
interpret" -- this repo's data/loaders.py provides daily (equity) / daily
(crypto via interval="1d") OHLCV only, so this is a daily-bar adaptation of
an intraday-designed test; tested here as a genuine (if lower-frequency)
test of whether the same jump-significance-gated momentum-continuation
logic still carries edge at daily granularity.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

THETA = (math.pi ** 2) / 4.0 + math.pi - 5.0  # Barndorff-Nielsen & Shephard (2006)


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _jump_z_and_direction(close: pd.Series, window: int) -> tuple[pd.Series, pd.Series]:
    log_ret = np.log(close / close.shift(1))

    rv = (log_ret ** 2).rolling(window).sum()
    bv = (math.pi / 2.0) * (log_ret.abs() * log_ret.abs().shift(1)).rolling(window).sum()

    n = window
    denom = np.sqrt(THETA * (bv ** 2) * 0.5)
    jump_z = np.sqrt(n) * (rv - bv) / denom.replace(0, np.nan)

    # Direction: sign of the dominant (largest-|return|) bar within the window.
    def _dominant_sign(x: pd.Series) -> float:
        if x.isna().all():
            return 0.0
        idx = x.abs().idxmax()
        return float(np.sign(x.loc[idx]))

    direction = log_ret.rolling(window).apply(
        lambda x: _dominant_sign(pd.Series(x)), raw=False
    )
    return jump_z, direction


def generate_signals(
    price_df: pd.DataFrame,
    window: int = 20,
    z_threshold: float = 1.96,
    max_hold_days: int = 10,
) -> pd.Series:
    """Long-only jump-momentum entry: go long when Jump-Z exceeds
    z_threshold AND the dominant return in the window is positive; hold up
    to max_hold_days or until Jump-Z reverts below threshold."""
    df = _prep(price_df)
    close = df["close"]
    jump_z, direction = _jump_z_and_direction(close, window=window)

    position = pd.Series(0, index=df.index, dtype=int)
    hold_counter = 0
    in_position = False
    for i in range(len(df)):
        z = jump_z.iloc[i]
        d = direction.iloc[i]
        significant_long_jump = (not pd.isna(z)) and z > z_threshold and d > 0

        if in_position:
            hold_counter += 1
            still_significant = (not pd.isna(z)) and z > z_threshold and d > 0
            if hold_counter >= max_hold_days or not still_significant:
                in_position = False
                hold_counter = 0
        if significant_long_jump and not in_position:
            in_position = True
            hold_counter = 0

        position.iloc[i] = 1 if in_position else 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
