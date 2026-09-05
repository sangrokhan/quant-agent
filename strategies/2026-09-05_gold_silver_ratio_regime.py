"""Strategy: Gold/Silver ratio z-score mean-reversion regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-030):
The gold/silver price ratio (GLD close / SLV close) is a widely-cited
contrarian mean-reversion signal: historically considered "low" below
~35:1 (gold cheap vs silver -> expect gold to outperform/silver to
underperform going forward) and "high" above ~80:1 (gold expensive vs
silver -> expect the reverse), per
https://www.quantifiedstrategies.com/gold-silver-chart-ratio-strategy/.
That source's OWN backtests found this signal erratic/unprofitable
applied directly to GLD, and explicitly states they "failed to find any
meaningful profitable trading strategy" using the ratio as a general
equity risk-on/off gauge either -- this strategy tests that specific
equity/crypto regime-filter framing anyway (rather than the metals pair
trade), using a rolling z-score (not the fixed 35/80 absolute levels,
which don't adapt to the ratio's long-run drift/2020 spike to 114) so the
threshold is comparable across the multi-year backtest window.

This continues the "cross-asset macro regime filter as long/flat gate for
equity+crypto" family in this repo (yield-curve un-inversion
2026-09-05-024, HYG/LQD credit spread 2026-09-05-025, DXY 50d SMA
2026-09-05-026, VIX/VIX3M term structure 2026-09-05-028, SKEW tail-risk
2026-09-05-029 -- all rejected so far) but is the first to use a
commodities-market (not bond/credit/FX/options-market) relative-value
signal.

Signal logic
------------
- ratio = close(GLD) / close(SLV).
- Rolling z-score of ratio over `ratio_lookback` days.
- Long (risk-on) when z-score <= low_z_threshold (gold historically cheap
  vs silver -> the source's own contrarian framing associates this with
  a broader risk-on/reflationary backdrop, silver being the more
  cyclical/industrial metal); flat when z-score >= high_z_threshold
  (gold historically expensive vs silver -> flight-to-safety/risk-off
  framing). Between the two thresholds: hold the prior state (no signal
  change) to avoid whipsaw in the "normal" middle zone.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity  # noqa: E402

_ratio_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def _get_ratio(start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    """Fetch GLD/SLV close ratio series covering [start, end], cached."""
    key = (start.date().isoformat(), end.date().isoformat())
    if key in _ratio_cache:
        return _ratio_cache[key]

    fetch_start = datetime(max(start.year - 2, 2000), 1, 1, tzinfo=timezone.utc)
    fetch_end = datetime(end.year + 1, 1, 1, tzinfo=timezone.utc)

    gld = load_equity("GLD", fetch_start, fetch_end)
    slv = load_equity("SLV", fetch_start, fetch_end)

    gld = gld.set_index(pd.to_datetime(gld["timestamp"], utc=True))["close"]
    slv = slv.set_index(pd.to_datetime(slv["timestamp"], utc=True))["close"]

    ratio = (gld / slv).dropna()
    ratio = ratio[~ratio.index.duplicated(keep="first")].sort_index()
    _ratio_cache[key] = ratio
    return ratio


def generate_signals(
    price_df: pd.DataFrame,
    ratio_lookback: int = 252,
    low_z_threshold: float = -1.0,
    high_z_threshold: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series from the GLD/SLV ratio regime."""
    df = _prep(price_df)
    idx = df.index

    ratio_full = _get_ratio(idx.min(), idx.max())
    ratio = ratio_full.reindex(idx, method="ffill").bfill()

    ratio_mean = ratio.rolling(ratio_lookback, min_periods=ratio_lookback // 2).mean()
    ratio_std = ratio.rolling(ratio_lookback, min_periods=ratio_lookback // 2).std()
    z = ((ratio - ratio_mean) / ratio_std).fillna(0.0)

    position = pd.Series(0, index=idx, dtype=int)
    state = 1  # default long/risk-on
    for i in range(len(idx)):
        zi = float(z.iloc[i])
        if zi <= low_z_threshold:
            state = 1
        elif zi >= high_z_threshold:
            state = 0
        # else: hold prior state
        position.iloc[i] = state
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
