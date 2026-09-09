"""Strategy: TIP/IEF ratio z-score inflation-regime filter for equities.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-027):
Per AllocateSmartly's review of David Varadi's "Inflation Compass" strategy
(allocatesmartly.com), the 5-year TIPS breakeven inflation rate (nominal
Treasury yield minus TIPS yield) is a market-based proxy for inflation
expectations that drives sector/asset rotation between growth-sensitive and
defensive assets. That full strategy requires FRED's T5YIE series (not
available via this repo's yfinance/ccxt loaders) plus an undisclosed exact
"sector-implied expected inflation" formula, so it's not reproducible
faithfully. This strategy tests a simplified, fully-testable proxy instead:
the price RATIO of TIP (iShares TIPS Bond ETF) to IEF (iShares 7-10yr
Treasury Bond ETF) approximates the same TIPS-vs-nominal-bond relative
pricing signal (rising ratio = TIPS outperforming nominal bonds = rising
inflation expectations priced in). Framed the same "cyclical/macro regime
filter for equities" way as the already-tested copper/gold and lumber/gold
ratios in this repo: rising inflation expectations (risk-on proxy here,
since moderate/rising inflation historically accompanies growth) gates a
long SPY/QQQ position; falling ratio (disinflation/deflation scare) gates
flat.

Uses the same adaptive rolling z-score + hysteresis-band mechanism as
2026-09-05-030 (gold/silver) and 2026-09-05-031 (copper/gold) rather than
a fixed absolute threshold, so it's comparable across the sample period.
First TIPS-based inflation-expectations proxy strategy in this repo,
distinct from every prior ratio-regime filter (copper/gold, lumber/gold,
XLU/SPY beta rotation, growth/value IVW/IVE, HYG/LQD credit spread).

Signal logic
------------
- ratio = close(TIP) / close(IEF).
- Rolling z-score of ratio over `ratio_lookback` days.
- Long (risk-on) when z-score >= high_z_threshold (TIPS outperforming
  nominal Treasuries -> rising inflation expectations).
- Flat (risk-off) when z-score <= low_z_threshold (TIPS underperforming ->
  falling/disinflationary expectations).
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
    """Fetch TIP/IEF close ratio series covering [start, end], cached."""
    key = (start.date().isoformat(), end.date().isoformat())
    if key in _ratio_cache:
        return _ratio_cache[key]

    fetch_start = datetime(max(start.year - 2, 2003), 1, 1, tzinfo=timezone.utc)
    fetch_end = datetime(end.year + 1, 1, 1, tzinfo=timezone.utc)

    tip = load_equity("TIP", fetch_start, fetch_end)
    ief = load_equity("IEF", fetch_start, fetch_end)

    tip = tip.set_index(pd.to_datetime(tip["timestamp"], utc=True))["close"]
    ief = ief.set_index(pd.to_datetime(ief["timestamp"], utc=True))["close"]

    ratio = (tip / ief).dropna()
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
