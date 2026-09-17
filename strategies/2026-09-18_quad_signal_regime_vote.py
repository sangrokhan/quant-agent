"""Strategy: Quad-Signal Risk-On Regime Vote (QQQ/cash rotation), inspired by
the "Quad Risk K2" QLD/ZROZ rotation family.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-005):
Per a Reddit r/LETFs post ("I backtested QLD/TQQQ rotation rules from
1986-2026", https://www.reddit.com/r/LETFs/comments/1tbnksd/, read via
browser_exec after web_search DDGS/Yahoo backend errored with TLS
RequestError on every query attempted this iteration): the author's
"Quad Risk K2" strategy holds a leveraged long ETF (QLD) when at least 2
of 4 binary regime signals are true (long trend, medium trend, realized
volatility, and short-term return persistence), otherwise rotates to a
defensive asset (ZROZ). The post discloses the STRUCTURE (4-signal
majority vote, >=2-of-4 threshold) and the qualitative signal categories
but not their exact numeric definitions (which live behind the author's
own dashboard/tool, not disclosed in the post text itself). This
iteration operationalizes the four categories with this repo's own
standard constructions (long trend = close>SMA(200); medium trend =
close>SMA(50); realized volatility = 20d realized vol <= its own trailing
252d median; short-term return persistence = 20-day return > 0), applies
the same >=vote_threshold-of-4 majority-vote gate, and trades the
UN-leveraged underlying (QQQ) rather than QLD/TQQQ (this repo's 0.25 MDD
threshold does not tolerate leveraged-ETF drawdown profiles, as already
confirmed by several prior TQQQ/QLD-flavored entries in this repo). First
multi-signal majority-vote REGIME (not entry-trigger) strategy in this
repo using this specific 4-category vote structure -- distinct from the
already-tested single-indicator majority-vote entries (e.g. Slope
Divergence 2026-09-17-120, a 3-window slope-divergence vote, not a
4-category cross-indicator regime vote).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position series).
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    long_trend_window: int = 200,
    medium_trend_window: int = 50,
    vol_window: int = 20,
    vol_lookback: int = 252,
    persistence_window: int = 20,
    vote_threshold: int = 2,
) -> pd.Series:
    """Return a {0,1} long/flat position series (>=vote_threshold of 4
    regime signals must agree for a long position)."""
    df = _prep(price_df)
    close = df["close"]

    long_trend = close > close.rolling(long_trend_window).mean()
    medium_trend = close > close.rolling(medium_trend_window).mean()

    daily_log_ret = (close / close.shift(1)).apply(
        lambda r: math.log(r) if r and r > 0 else None
    ).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    low_vol = realized_vol <= vol_median

    persistence = close.pct_change(persistence_window) > 0

    votes = (
        long_trend.fillna(False).astype(int)
        + medium_trend.fillna(False).astype(int)
        + low_vol.fillna(False).astype(int)
        + persistence.fillna(False).astype(int)
    )

    position = (votes >= vote_threshold).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
