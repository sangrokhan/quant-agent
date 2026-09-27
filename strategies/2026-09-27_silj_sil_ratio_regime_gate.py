"""Strategy: SILJ/SIL (junior vs senior silver miners) ratio regime gate on
SMA trend-following.

Hypothesis (2026-09-27 KB entry, this iteration): per
https://discoveryalert.com/education/silver-mining-equities-sil-silj-guide/
(junior silver miners, SILJ, carry substantially higher operating leverage
to silver-price moves than senior/large-cap silver miners, SIL -- "50-100%
leverage on price moves"), a rising SILJ/SIL ratio (juniors outperforming
seniors) proxies elevated risk appetite for the highest-beta names in an
already-high-beta sub-sector, extending this repo's already-validated
GDX/GLD ratio-regime-gate pattern (2026-09-11-049/065, accepted QQQ+SPY) one
level further down the risk-appetite spectrum: silver JUNIOR miners vs
silver SENIOR miners, rather than gold miners vs gold bullion. First
SIL/SILJ strategy in this repo (0 prior KB hits for SIL/SILJ) -- distinct
from the existing GDX/GLD gate (different metal, and compares miners-of-any-
size vs the metal itself rather than junior-vs-senior miners).

Architecturally identical construction to the accepted GDX/GLD gate: long
the primary asset's own SMA-trend-following signal only when the
SILJ/SIL ratio is above its own rolling SMA (risk-on proxy); flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import sys
import os
from datetime import datetime, timezone

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

_ratio_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_silj_sil_gate(index: pd.DatetimeIndex, ratio_sma_window: int) -> pd.Series:
    """Load SILJ and SIL closes, compute SILJ/SIL ratio vs its own rolling
    SMA gate (True = ratio above SMA = junior miners outperforming senior
    miners = risk-on proxy), reindexed to match the primary asset's index."""
    cache_key = ratio_sma_window
    if cache_key in _ratio_cache:
        gate = _ratio_cache[cache_key]
    else:
        from loaders import load_equity

        start = index.min().to_pydatetime() if len(index) else datetime(2015, 1, 1)
        end = index.max().to_pydatetime() if len(index) else datetime(2026, 9, 1)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        pad_start = start.replace(year=max(start.year - 2, 2013))

        silj_close = _prep(load_equity("SILJ", pad_start, end))["close"]
        sil_close = _prep(load_equity("SIL", pad_start, end))["close"]
        ratio = (silj_close / sil_close).dropna()
        ratio_sma = ratio.rolling(ratio_sma_window).mean()
        gate = (ratio > ratio_sma).astype(int)
        _ratio_cache[cache_key] = gate

    reindexed = gate.reindex(index, method="ffill").fillna(0).astype(int)
    return reindexed


def generate_signals(
    price_df: pd.DataFrame,
    trend_sma_window: int = 200,
    ratio_sma_window: int = 100,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 10.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long when close > own trend_sma_window-day SMA AND SILJ/SIL ratio is
    above its own ratio_sma_window-day SMA (junior silver miners
    outperforming senior silver miners -- risk-on/high-beta-appetite
    proxy) AND trailing vol_window-day realized vol <= vol_regime_ratio x
    its trailing vol_lookback-day median (low/normal-vol regime gate,
    rescuing the near-miss full-sample Sharpe recorded at
    2026-09-27-063 -- the un-gated version's edge is concentrated in the
    low-vol tercile per that grid test); flat otherwise. Default
    vol_regime_ratio=10.0 is effectively a no-op (matches the un-gated
    2026-09-27-063 behavior) unless explicitly tightened by the caller.
    """
    import math

    df = _prep(price_df)
    close = df["close"]

    own_sma = close.rolling(trend_sma_window).mean()
    own_trend_up = close > own_sma

    ratio_gate = _load_silj_sil_gate(df.index, ratio_sma_window)

    daily_log_ret = (close / close.shift(1)).apply(
        lambda r: math.log(r) if r and r > 0 else None
    ).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    low_vol_regime = (realized_vol <= (vol_median * vol_regime_ratio)).fillna(False)

    position = (own_trend_up.astype(int) & ratio_gate & low_vol_regime.astype(int)).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
