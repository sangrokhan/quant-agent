"""Strategy: XLY/XLP consumer discretionary-vs-staples ratio MA regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-037):
The XLY/XLP ratio (consumer discretionary sector ETF / consumer staples
sector ETF) is a classic risk-on/risk-off gauge: when discretionary
(cyclical, luxury/travel/retail spending) outperforms staples (defensive,
non-cyclical necessities), it signals investors expect continued economic
strength/risk appetite. Per multiple sources found via web search/browser
fallback (web_search backend intermittently failing this session) --
e.g. zForex: "Investors are shifting into risk-on mode when discretionary
stocks lead staples"; Seeking Alpha: "When this ratio is rising... risk
appetite is increasing" -- and per ETFreplay's general "Ratio MA" regime-
switch methodology (https://www.etfreplay.com/blog/regime-change/,
illustrated there with a different pair, SCHG/FNDX): invest risk-on when
ratio > its own N-period MA, risk-off when ratio < MA.

This continues the cross-asset/cross-sector ratio regime-filter family in
this repo (gold/silver 2026-09-05-030 accepted; copper/gold 2026-09-05-032
near-miss rejected; RSP/SPY 2026-09-05-034 rejected; SPY/TLT
2026-09-05-036 rejected) -- this is the first to use a sector-rotation
(within-equity-market) signal rather than a cross-asset-class one.

Signal logic
------------
- ratio = close(XLY) / close(XLP).
- `ma_window`-period SMA of the ratio.
- Long when ratio > its own SMA (discretionary leading staples,
  risk-on); flat when ratio < SMA (staples leading, risk-off).

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
    """Fetch XLY/XLP close ratio series covering [start, end], cached."""
    key = (start.date().isoformat(), end.date().isoformat())
    if key in _ratio_cache:
        return _ratio_cache[key]

    fetch_start = datetime(max(start.year - 2, 2000), 1, 1, tzinfo=timezone.utc)
    fetch_end = datetime(end.year + 1, 1, 1, tzinfo=timezone.utc)

    xly = load_equity("XLY", fetch_start, fetch_end)
    xlp = load_equity("XLP", fetch_start, fetch_end)

    xly = xly.set_index(pd.to_datetime(xly["timestamp"], utc=True))["close"]
    xlp = xlp.set_index(pd.to_datetime(xlp["timestamp"], utc=True))["close"]

    ratio = (xly / xlp).dropna()
    ratio = ratio[~ratio.index.duplicated(keep="first")].sort_index()
    _ratio_cache[key] = ratio
    return ratio


def generate_signals(
    price_df: pd.DataFrame,
    ma_window: int = 84,  # ~4 trading months, per ETFreplay's best-performing length
) -> pd.Series:
    """Return a {0,1} long/flat position series from the XLY/XLP ratio MA regime."""
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
