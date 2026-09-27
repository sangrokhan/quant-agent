"""Strategy: GDXJ/GDX (junior vs senior gold miners) ratio regime gate on
SMA trend-following.

Hypothesis (2026-09-27 KB entry, this iteration): junior gold miners
(GDXJ) carry substantially higher operating leverage to gold-price moves
than senior/large-cap gold miners (GDX) -- the same "junior vs senior
miner leverage" dynamic documented for silver miners in
https://discoveryalert.com/education/silver-mining-equities-sil-silj-guide/
("junior miners deliver 50-100% leverage on price moves" relative to
seniors), generalized to gold's own junior/senior miner-ETF pair. A rising
GDXJ/GDX ratio (juniors outperforming seniors) proxies elevated risk
appetite for the highest-beta names in an already-high-beta sub-sector,
directly paralleling this same cron trigger's SILJ/SIL gate
(2026-09-27-063/064, accepted after a vol-regime rescue) but for gold
rather than silver. Distinct from the existing GDX/GLD gate
(2026-09-11-049/065, accepted) since that compares miners-of-any-size vs
the metal itself, not junior-vs-senior miners against each other. First
GDX/GDXJ junior-vs-senior strategy in this repo (0 prior KB hits for
"GDXJ").

Architecturally identical construction to the accepted GDX/GLD and
SILJ/SIL gates: long the primary asset's own SMA-trend-following signal
only when the GDXJ/GDX ratio is above its own rolling SMA (risk-on proxy)
AND (per the SILJ/SIL sibling's own vol-regime rescue precedent, applied
proactively here) a low/normal realized-vol regime gate; flat otherwise.

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


def _load_gdxj_gdx_gate(index: pd.DatetimeIndex, ratio_sma_window: int) -> pd.Series:
    """Load GDXJ and GDX closes, compute GDXJ/GDX ratio vs its own rolling
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

        gdxj_close = _prep(load_equity("GDXJ", pad_start, end))["close"]
        gdx_close = _prep(load_equity("GDX", pad_start, end))["close"]
        ratio = (gdxj_close / gdx_close).dropna()
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

    Long when close > own trend_sma_window-day SMA AND GDXJ/GDX ratio is
    above its own ratio_sma_window-day SMA (junior gold miners
    outperforming senior gold miners -- risk-on/high-beta-appetite proxy)
    AND trailing vol_window-day realized vol <= vol_regime_ratio x its
    trailing vol_lookback-day median; flat otherwise. Default
    vol_regime_ratio=10.0 is effectively a no-op (unconditional pass)
    unless explicitly tightened by the caller -- matching the SILJ/SIL
    sibling's convention.
    """
    import math

    df = _prep(price_df)
    close = df["close"]

    own_sma = close.rolling(trend_sma_window).mean()
    own_trend_up = close > own_sma

    ratio_gate = _load_gdxj_gdx_gate(df.index, ratio_sma_window)

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
