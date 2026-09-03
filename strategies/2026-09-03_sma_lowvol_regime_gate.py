"""Strategy: SMA(200) trend-following, gated to trade only in a low-volatility
regime (ex-ante realized-vol percentile filter).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-03-021),
sourced from a Reddit r/algotrading discussion on market regime filters
(surfaced in Google search results for "low volatility regime filter trend
following strategy only trade when volatility low rules"): "On the
volatility filter thresholds I use 35% for low and 65% for the high
volatility threshold and 150-250 bars look back." I.e. classify each day's
trailing realized volatility into low/mid/high terciles using its
percentile rank within a rolling ~200-bar lookback window, and gate a
trend-following signal to only fire in the low-vol regime.

This strategy is also directly motivated by an accumulated finding already
present in THIS repo's own knowledge base: nearly every trend/momentum
strategy tested so far (Donchian -008, momentum -002/-003/-004/-012, MACD
-013, SuperTrend -014, Keltner -016, 52wk-high -015, ADX -017) shows the
SAME post-hoc pattern in its grid_test vol-regime breakdown -- passing
disproportionately in the low-vol tercile and failing near-universally in
the high-vol tercile. All of those strategies discovered this pattern only
AFTER the fact (via grid_test's by_vol_regime slicing), never ex-ante
gating on it. This strategy tests whether EXPLICITLY gating a simple SMA
trend-follow signal to only trade when the CURRENT realized-vol percentile
(computed causally, using only trailing data) is low -- i.e. skipping
trades outright during medium/high-vol regimes rather than just passively
observing the pattern after the fact -- improves the full-sample Sharpe/MDD
of a basic long-only SMA(50) > SMA(200) golden-cross trend strategy, since
avoiding high-vol regime whipsaw entirely (rather than accepting the drag)
is the natural next step suggested by the accumulated evidence.

Interface contract for validators (see validation/validators.py) and grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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
    fast_window: int = 50,
    slow_window: int = 200,
    vol_window: int = 20,
    vol_lookback: int = 200,
    low_vol_percentile: float = 0.35,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Base signal: golden-cross trend-follow, long when
    SMA(fast_window) > SMA(slow_window).
    Vol gate: causal `vol_window`-day realized volatility (std of daily
    returns), ranked as a rolling percentile within the trailing
    `vol_lookback` days; only allow the base signal to be long when that
    percentile is <= `low_vol_percentile` (default 0.35, i.e. only trade
    in the bottom 35% least-volatile trailing conditions). Both the SMA
    and the vol-percentile computation use only data available as of each
    bar (rolling windows, no centering), so no look-ahead beyond the
    standard 1-day position shift applied in generate_returns.
    """
    df = _prep(price_df)
    close = df["close"]

    sma_fast = close.rolling(fast_window).mean()
    sma_slow = close.rolling(slow_window).mean()
    trend_signal = (sma_fast > sma_slow).astype(int)

    daily_ret = close.pct_change()
    realized_vol = daily_ret.rolling(vol_window).std()
    vol_pctile = realized_vol.rolling(vol_lookback).apply(
        lambda x: (x.rank(pct=True).iloc[-1]) if len(x.dropna()) > 1 else float("nan"),
        raw=False,
    )
    low_vol_gate = (vol_pctile <= low_vol_percentile).astype(int)

    position = trend_signal * low_vol_gate
    return position.fillna(0).astype(int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
