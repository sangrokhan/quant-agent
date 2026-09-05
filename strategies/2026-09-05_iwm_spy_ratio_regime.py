"""Strategy: IWM/SPY small-cap-vs-large-cap ratio MA regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-039):
The IWM/SPY ratio (Russell 2000 small-cap ETF / S&P 500 large-cap ETF) is a
classic risk-appetite "thermometer": when small caps (IWM) lead large caps
(SPY), it signals a broadening, risk-on market with investors rotating into
higher-beta domestically-focused names; when SPY leads (IWM underperforms),
it signals defensive flight to large-cap stability. Per
https://tradethepool.com/fundamental/what-are-small-cap-stocks-the-complete-guide-for-traders/
("The Russell 2000 (IWM) serves as the ultimate 'risk-on' thermometer... When
IWM leads SPY, it indicates a broadening market") and Google's AI-overview
summary (citing StockCharts) of an "IWM/SPY Relative Strength Spread" with a
20-50 day lookback rotation trigger. Neither source publishes a specific
backtested threshold, so this applies the same ratio-MA-regime mechanism
already validated for gold/silver (2026-09-05-030, accepted) and XLY/XLP
(2026-09-05-038, accepted): long when ratio > its own trailing SMA, flat
otherwise. Distinct from those two -- first small-cap/large-cap-benchmark
ratio (rather than a commodity pair or same-market sector pair).

Signal logic
------------
- ratio = close(IWM) / close(SPY).
- `ma_window`-period SMA of the ratio.
- Long when ratio > its own SMA (small caps leading, risk-on); flat when
  ratio < SMA (large caps leading, risk-off/defensive).

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
    """Fetch IWM/SPY close ratio series covering [start, end], cached."""
    key = (start.date().isoformat(), end.date().isoformat())
    if key in _ratio_cache:
        return _ratio_cache[key]

    fetch_start = datetime(max(start.year - 2, 2000), 1, 1, tzinfo=timezone.utc)
    fetch_end = datetime(end.year + 1, 1, 1, tzinfo=timezone.utc)

    iwm = load_equity("IWM", fetch_start, fetch_end)
    spy = load_equity("SPY", fetch_start, fetch_end)

    iwm = iwm.set_index(pd.to_datetime(iwm["timestamp"], utc=True))["close"]
    spy = spy.set_index(pd.to_datetime(spy["timestamp"], utc=True))["close"]

    ratio = (iwm / spy).dropna()
    ratio = ratio[~ratio.index.duplicated(keep="first")].sort_index()
    _ratio_cache[key] = ratio
    return ratio


def generate_signals(
    price_df: pd.DataFrame,
    ma_window: int = 50,  # ~2.5 trading months, per the source's "20-50 day lookback"
) -> pd.Series:
    """Return a {0,1} long/flat position series from the IWM/SPY ratio MA regime."""
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
