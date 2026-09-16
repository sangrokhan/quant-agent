"""Strategy: Platinum/Palladium ratio z-score mean-reversion regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-055):
The platinum/palladium price ratio (PPLT close / PALL close) is a
precious-metals relative-value indicator with the SAME "mean-reverting
extremes" framing as the already-tested gold/silver ratio
(2026-09-05-030, accepted as an equity regime gate), but driven by a
DIFFERENT economic mechanism: per goldpriceforecast.com's "Platinum to
Palladium Ratio" explainer, the ratio has historically ranged 0.6-5.3
(average ~2.8) since 1990, and "if the ratio moves to extremes, it
creates a trading opportunity" -- a high ratio means palladium may be
oversold (buying opportunity for palladium / bearish signal for
platinum-relative positioning), a low ratio the reverse. Unlike
gold/silver (both largely investment/store-of-value demand), platinum
and palladium prices are driven primarily by AUTO-CATALYST industrial
substitution economics (diesel vs gasoline catalytic converters), so
their ratio is a genuinely distinct commodity-market signal, not a
re-parameterization of the existing gold/silver regime filter.

First platinum/palladium-ratio strategy in this repo (0 prior hits on
"platinum" or "palladium" in strategies_index.jsonl). Applies the exact
same rolling-z-score regime-gate construction validated for GLD/SLV
(rather than the raw historical-average absolute levels, which don't
adapt over a multi-year backtest window) as a long/flat gate for the
existing equity+crypto universe.

Signal logic
------------
- ratio = close(PPLT) / close(PALL).
- Rolling z-score of ratio over `ratio_lookback` days.
- Long (risk-on) when z-score <= low_z_threshold (platinum historically
  cheap vs palladium -> per source, ratio-extreme-low framing associates
  with palladium being relatively overbought / platinum being the
  contrarian long -- used here as a broad risk-on regime signal, mirroring
  the GLD/SLV framing); flat when z-score >= high_z_threshold (platinum
  historically expensive vs palladium -> risk-off). Between the two
  thresholds: hold the prior state (no signal change) to avoid whipsaw in
  the "normal" middle zone.

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
    """Fetch PPLT/PALL close ratio series covering [start, end], cached."""
    key = (start.date().isoformat(), end.date().isoformat())
    if key in _ratio_cache:
        return _ratio_cache[key]

    fetch_start = datetime(max(start.year - 2, 2000), 1, 1, tzinfo=timezone.utc)
    fetch_end = datetime(end.year + 1, 1, 1, tzinfo=timezone.utc)

    pplt = load_equity("PPLT", fetch_start, fetch_end)
    pall = load_equity("PALL", fetch_start, fetch_end)

    pplt = pplt.set_index(pd.to_datetime(pplt["timestamp"], utc=True))["close"]
    pall = pall.set_index(pd.to_datetime(pall["timestamp"], utc=True))["close"]

    ratio = (pplt / pall).dropna()
    ratio = ratio[~ratio.index.duplicated(keep="first")].sort_index()
    _ratio_cache[key] = ratio
    return ratio


def generate_signals(
    price_df: pd.DataFrame,
    ratio_lookback: int = 252,
    low_z_threshold: float = -1.0,
    high_z_threshold: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series from the PPLT/PALL ratio regime."""
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
