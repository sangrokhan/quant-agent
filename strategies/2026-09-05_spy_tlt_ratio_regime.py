"""Strategy: SPY/TLT stock-vs-bond ratio SMA-crossover regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-035):
The SPY/TLT ratio (S&P 500 ETF / 20+yr Treasury bond ETF) tracks whether
investors are favoring equities or long-duration Treasuries -- a classic
stock-vs-bond risk regime signal. Per
https://aveceasar.github.io/ratios/spy-tlt/ (ChartVault charting tool,
"How To Read It": "A rising line means SPY is outperforming TLT; a
falling line means TLT is taking the lead... the most important reversals
are the ones that break a long trend"), this strategy operationalizes a
fast/slow SMA crossover on the ratio itself: fast SMA > slow SMA means
stocks are leading (risk-on, go long the traded asset), fast SMA < slow
SMA means bonds are leading (risk-off/flight-to-safety, go flat).

Distinct from the yield-curve un-inversion (2026-09-05-024) and HYG/LQD
credit-spread (2026-09-05-025) strategies in this repo, which both use
bond-market-internal signals (yield curve shape, credit spread) rather
than a direct stock-vs-bond relative-strength ratio.

Signal logic
------------
- ratio = close(SPY) / close(TLT).
- fast SMA (`fast_window`) vs slow SMA (`slow_window`) of the ratio.
- Long when fast SMA > slow SMA (stocks leading bonds); flat otherwise.

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
    """Fetch SPY/TLT close ratio series covering [start, end], cached."""
    key = (start.date().isoformat(), end.date().isoformat())
    if key in _ratio_cache:
        return _ratio_cache[key]

    fetch_start = datetime(max(start.year - 2, 2000), 1, 1, tzinfo=timezone.utc)
    fetch_end = datetime(end.year + 1, 1, 1, tzinfo=timezone.utc)

    spy = load_equity("SPY", fetch_start, fetch_end)
    tlt = load_equity("TLT", fetch_start, fetch_end)

    spy = spy.set_index(pd.to_datetime(spy["timestamp"], utc=True))["close"]
    tlt = tlt.set_index(pd.to_datetime(tlt["timestamp"], utc=True))["close"]

    ratio = (spy / tlt).dropna()
    ratio = ratio[~ratio.index.duplicated(keep="first")].sort_index()
    _ratio_cache[key] = ratio
    return ratio


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 20,
    slow_window: int = 50,
) -> pd.Series:
    """Return a {0,1} long/flat position series from the SPY/TLT ratio SMA crossover."""
    df = _prep(price_df)
    idx = df.index

    ratio_full = _get_ratio(idx.min(), idx.max())
    ratio = ratio_full.reindex(idx, method="ffill").bfill()

    fast_sma = ratio.rolling(fast_window, min_periods=fast_window // 2).mean()
    slow_sma = ratio.rolling(slow_window, min_periods=slow_window // 2).mean()

    position = (fast_sma > slow_sma).fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
