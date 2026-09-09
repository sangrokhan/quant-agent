"""Strategy: Consistent Momentum (single-asset time-series adaptation),
long-only, on daily bars.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per Quantpedia's "Consistent Momentum Strategy" summary (based on academic
research showing only ~60% of winner/loser stocks are "consistent"
winners/losers -- positive momentum in BOTH the formation month AND the
following month -- and that CONSISTENT winners significantly outperform
INCONSISTENT winners in the post-formation period): momentum's edge is
concentrated in assets whose recent momentum is persistent/consistent
across two consecutive sub-periods, not just present in a single lookback
window.

Adapted from the source's cross-sectional decile-sort design (not
directly testable with this repo's single-symbol OHLCV loaders) to a
single-asset time-series analog: define "consistency" as the trailing
lookback-day return being positive in BOTH the most recent lookback-day
window AND the lookback-day window immediately before it (two
non-overlapping consecutive windows must both show positive momentum,
rather than a single window as in standard time-series momentum already
tested in this repo, e.g. 2026-09-03-012). Long only when both windows
are positive (consistent winner state); flat otherwise (including the
"inconsistent" single-positive-window case the source shows underperforms
a true consistent winner). Rebalanced daily (looser than the source's
6-month formation period, adapted to this repo's daily-bar convention),
gated by a max_hold_days safety exit is NOT used here since the position
naturally flips when consistency breaks.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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
    lookback_days: int = 21,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Consistent-winner state: trailing `lookback_days` return is positive
    AND the trailing return over the PRIOR (non-overlapping) window of the
    same length is also positive.
    """
    df = _prep(price_df)
    close = df["close"]

    recent_window_ret = close / close.shift(lookback_days) - 1.0
    prior_window_ret = close.shift(lookback_days) / close.shift(2 * lookback_days) - 1.0

    consistent_winner = (recent_window_ret > 0) & (prior_window_ret > 0)
    position = consistent_winner.fillna(False).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    lookback_days: int = 21,
) -> pd.Series:
    """Daily strategy returns (no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(price_df, lookback_days=lookback_days)

    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_ret
