"""Strategy: Multi-horizon time-series momentum blend (1/3/12-month voting).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-132):
Per https://summitward.com/learn/crypto-trend-following's summary of the
time-series momentum literature (Moskowitz/Ooi/Pedersen and practitioner
trend-following programs): "Practitioners usually blend several horizons,
most commonly 1, 3, and 12 months, because no single lookback is reliably
best and the blend avoids betting on one." This repo has tested many
SINGLE-lookback momentum/trend constructions (SMA200, 52-week-high, ROC,
Coppock, KST, etc.) but never an explicit multi-horizon BLEND/VOTE
construction, which is the industry-standard way trend-following programs
are actually built (per the source's own citation of replication-fund
research finding "these families perform so similarly that hunting for the
one magic indicator is a waste of effort; diversifying across simple
versions of all four is the defensible choice" -- applied here across
lookback horizons rather than indicator families).

Signal logic
------------
- Three trailing total-return lookbacks: `short_days` (~1 month, default
  21), `mid_days` (~3 months, default 63), `long_days` (~12 months, default
  252).
- At each bar, compute sign(trailing return) for each horizon (+1 if
  positive, -1 if negative or NaN during warmup).
- Long when the SUM of the three signs is >= `min_votes` (default 2, i.e.
  at least 2 of 3 horizons agree bullish -- a majority vote, not requiring
  unanimous agreement across all three, since "no single lookback is
  reliably best").
- Flat when the vote sum is < `min_votes`.
- No stop-loss/time-stop -- position tracks the vote state directly each
  bar (this mirrors this repo's other regime-state constructions, e.g. the
  accepted Laguerre RSI zero-line regime filter 2026-09-06-110, rather than
  a discrete-trigger-then-timed-exit pattern).

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    short_days: int = 21,
    mid_days: int = 63,
    long_days: int = 252,
    min_votes: int = 2,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ret_short = close.pct_change(short_days)
    ret_mid = close.pct_change(mid_days)
    ret_long = close.pct_change(long_days)

    sign_short = ret_short.apply(lambda v: 1 if (v is not None and v > 0) else (-1 if v is not None and v <= 0 else 0))
    sign_mid = ret_mid.apply(lambda v: 1 if (v is not None and v > 0) else (-1 if v is not None and v <= 0 else 0))
    sign_long = ret_long.apply(lambda v: 1 if (v is not None and v > 0) else (-1 if v is not None and v <= 0 else 0))

    # During warmup (NaN return), treat that horizon's vote as 0 (abstain)
    # rather than penalizing/crediting it, since we have no data yet.
    sign_short = sign_short.where(ret_short.notna(), 0)
    sign_mid = sign_mid.where(ret_mid.notna(), 0)
    sign_long = sign_long.where(ret_long.notna(), 0)

    vote_sum = sign_short + sign_mid + sign_long
    position = (vote_sum >= min_votes).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
