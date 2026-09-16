"""Strategy: XLK/XLU technology-vs-utilities ratio 200-day SMA regime filter.

Source: https://www.quantifiedstrategies.com/xlk-xlu-ratio-trading-strategy/
(visited this iteration via browser_exec -- web_search DDGS/Yahoo backend
down with RequestError/TLS errors on every query attempted this iteration).
Precise trading rules were paywalled (members-only), but the article's own
disclosed methodology summary and backtest description give the concrete
construction used here: "Uses 200-day moving average as regime filter...
what if we invest in utilities when the ratio is below the 200-day SMA?"
First XLK/XLU ratio entry in this repo (0 prior KB hits) -- distinct from
this repo's other sector-rotation ratio strategies (XLY/XLP consumer
discretionary-vs-staples 2026-09-05-037, IWM/SPY, SOXX/QQQ, etc.) since
tech-vs-utilities is a more direct "growth appetite vs defensive/bond-proxy"
signal per the source's own framing ("Tech is mostly about growth, while
utility stocks are about value and preservation... during a bear market,
utilities outperform other sectors").

Signal logic (source's own disclosed construction, operationalized on this
repo's single-symbol OHLCV contract):
- ratio = close(XLK) / close(XLU).
- `ma_window`-period SMA of the ratio (default 200, matching the source's
  own stated "200-day moving average" regime filter).
- Long when ratio > its own SMA (tech leading utilities, risk-on/bullish
  per source's stated interpretation "A rising XLK/XLU is considered
  bullish"); flat when ratio < SMA (utilities leading, risk-off/bearish).

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
    """Fetch XLK/XLU close ratio series covering [start, end], cached."""
    key = (start.date().isoformat(), end.date().isoformat())
    if key in _ratio_cache:
        return _ratio_cache[key]

    fetch_start = datetime(max(start.year - 2, 2000), 1, 1, tzinfo=timezone.utc)
    fetch_end = datetime(end.year + 1, 1, 1, tzinfo=timezone.utc)

    xlk = load_equity("XLK", fetch_start, fetch_end)
    xlu = load_equity("XLU", fetch_start, fetch_end)

    xlk = xlk.set_index(pd.to_datetime(xlk["timestamp"], utc=True))["close"]
    xlu = xlu.set_index(pd.to_datetime(xlu["timestamp"], utc=True))["close"]

    ratio = (xlk / xlu).dropna()
    ratio = ratio[~ratio.index.duplicated(keep="first")].sort_index()
    _ratio_cache[key] = ratio
    return ratio


def generate_signals(
    price_df: pd.DataFrame,
    ma_window: int = 200,  # per source's own stated "200-day moving average" filter
) -> pd.Series:
    """Return a {0,1} long/flat position series from the XLK/XLU ratio MA regime."""
    df = _prep(price_df)
    idx = df.index

    ratio_full = _get_ratio(idx.min(), idx.max())
    ratio = ratio_full.reindex(idx, method="ffill").bfill()

    ma = ratio.rolling(ma_window, min_periods=ma_window // 2).mean()
    position = (ratio > ma).fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
