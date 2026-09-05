"""Strategy: Copper/Gold ratio z-score regime filter (equity/crypto).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-031):
The copper/gold ratio (HG=F copper futures / GC=F gold futures) is a
well-known macro barometer of cyclical growth (copper, industrial demand)
versus safe-haven/inflation-hedge demand (gold), per
https://www.quantifiedstrategies.com/copper-gold-ratio-trading-strategy/.
That source's own backtest rule (ratio < 0.19 for the first time in a
year -> buy copper AND gold themselves, strong 1-12mo forward returns) is
about timing entries into the commodities directly, not equities -- this
strategy instead tests the analogous "cyclical risk regime" framing
already validated for gold/silver (2026-09-05-030, accepted) applied here
to copper/gold: does a LOW (falling) copper/gold ratio -- signaling
economic slack / risk-off according to the source's own rationale -- work
as a FLAT/risk-off signal for equities, with a rising ratio (industrial
demand recovering) as the LONG/risk-on signal? This is the mirror-image
framing of the source's contrarian "buy the extreme low" trade: here we
treat a low/falling ratio as confirming risk-off (go flat) rather than as
a contrarian buy signal for the commodities themselves.

Uses the same adaptive rolling z-score + hysteresis-band mechanism as
2026-09-05-030 (gold/silver ratio) rather than the source's fixed 0.19
absolute level, so the threshold is comparable across regimes/format
(HG=F and GC=F futures continuous contract prices drift over the ~7yr
window).

Signal logic
------------
- ratio = close(HG=F) / close(GC=F).
- Rolling z-score of ratio over `ratio_lookback` days.
- Long (risk-on) when z-score >= high_z_threshold (copper strong vs gold
  -> growth/risk-on per the source's own rationale).
- Flat (risk-off) when z-score <= low_z_threshold (copper weak vs gold
  -> economic slack/risk-off).
- Hold prior state in between (hysteresis band, avoids whipsaw).

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
    """Fetch HG=F/GC=F close ratio series covering [start, end], cached."""
    key = (start.date().isoformat(), end.date().isoformat())
    if key in _ratio_cache:
        return _ratio_cache[key]

    fetch_start = datetime(max(start.year - 2, 2000), 1, 1, tzinfo=timezone.utc)
    fetch_end = datetime(end.year + 1, 1, 1, tzinfo=timezone.utc)

    copper = load_equity("HG=F", fetch_start, fetch_end)
    gold = load_equity("GC=F", fetch_start, fetch_end)

    copper = copper.set_index(pd.to_datetime(copper["timestamp"], utc=True))["close"]
    gold = gold.set_index(pd.to_datetime(gold["timestamp"], utc=True))["close"]

    ratio = (copper / gold).dropna()
    ratio = ratio[~ratio.index.duplicated(keep="first")].sort_index()
    _ratio_cache[key] = ratio
    return ratio


def generate_signals(
    price_df: pd.DataFrame,
    ratio_lookback: int = 252,
    low_z_threshold: float = -1.0,
    high_z_threshold: float = 0.5,
) -> pd.Series:
    """Return a {0,1} long/flat position series from the copper/gold ratio regime."""
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
        if zi >= high_z_threshold:
            state = 1
        elif zi <= low_z_threshold:
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
