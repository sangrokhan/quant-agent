"""Strategy: MSTR/BTC ratio ("mNAV proxy") regime gate on SMA trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-XXX):
Per mNAV.com, Simple Mining, Look Into Bitcoin, and BitMEX explainers of
Strategy Inc's (MSTR, formerly MicroStrategy) "multiple of Net Asset Value"
(mNAV) metric (Google SERP snippets, read via browser_exec this iteration
-- web_search DDGS backend returned no results for the query): mNAV = MSTR's
market cap / the fair value of its BTC holdings. "mNAV above 1.0 means MSTR
trades at a premium to the Bitcoin it holds; below 1.0 means a discount."
The premium historically expands during bitcoin bull-market euphoria
(peaked >2.4x in 2024, per Look Into Bitcoin) and compresses toward/below
1.0 during risk-off/capitulation phases (recent 2025-2026 compression to
~0.75x per a cited Reddit discussion, "confidence eroding").

Since this repo's data/loaders.py only exposes OHLCV (no MSTR balance-sheet
BTC-holdings/debt data needed for the true mNAV formula), this strategy
uses a directly observable PROXY: the price ratio MSTR_close / BTC_close.
This proxy is not the literal mNAV multiple (units differ, and MSTR's BTC
holdings/share count change over time), but it is monotonically related to
mNAV's premium/discount DIRECTION over medium horizons -- when MSTR
outperforms BTC, mNAV is expanding (equity-market risk appetite for
leveraged bitcoin exposure); when MSTR underperforms BTC, mNAV is
compressing (deleveraging/risk-off). The ratio being ABOVE its own rolling
SMA is treated as a "mNAV expanding / risk-on" regime gate applied to a
plain SMA trend-following signal on the traded asset itself -- mirroring
this repo's already-validated cross-asset ratio-gate pattern (GDX/GLD,
Copper/Gold, TLT/IEF, XLU/SPY) which is architecturally distinct from a
GDX/RING-style pairs mean-reversion trade.

First strategy in this repo to use MSTR (a corporate bitcoin-treasury
proxy) as a cross-asset signal source, and the first application of the
mNAV-premium concept as a systematic regime filter (as opposed to a manual
qualitative "is MSTR cheap/rich" read).

Tested on the intended domain (BTC/USDT, ETH/USDT -- the ratio is
economically about bitcoin-market sentiment) AND on equity (QQQ, SPY) as an
explicit falsification check (the ratio has no particular reason to gate
broad equity-index trend-following beyond a generic risk-on/risk-off proxy
role).

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
    df = df[~df.index.duplicated(keep="last")]
    return df


def _to_naive_daily(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """tz-naive, date-normalized copy of an index -- used ONLY for aligning
    the cross-asset (equity vs crypto) ratio lookup; the strategy's own
    generate_signals/generate_returns outputs always keep the ORIGINAL
    index (tz-aware, as passed in via price_df) so grid_test.py's
    vol-regime-mask reindex (which reindexes against the original price_df
    index) lines up correctly."""
    idx = pd.to_datetime(index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    return idx.normalize()


def _load_mnav_gate(index: pd.DatetimeIndex, ratio_sma_window: int) -> pd.Series:
    """Load MSTR (equity) and BTC/USDT (crypto, daily-resampled) closes,
    compute the MSTR/BTC ratio ("mNAV proxy") vs its own rolling SMA gate
    (True = ratio above SMA = mNAV expanding = risk-on), reindexed to match
    the primary asset's index. Cached across calls within a process."""
    cache_key = ratio_sma_window
    if cache_key in _ratio_cache:
        gate = _ratio_cache[cache_key]
    else:
        from loaders import load_equity, load_crypto

        start = index.min().to_pydatetime() if len(index) else datetime(2015, 1, 1)
        end = index.max().to_pydatetime() if len(index) else datetime(2026, 9, 1)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        pad_start = start.replace(year=max(start.year - 2, 2015))

        mstr_raw = _prep(load_equity("MSTR", pad_start, end))["close"]
        mstr_close = mstr_raw.copy()
        mstr_close.index = _to_naive_daily(mstr_close.index)
        mstr_close = mstr_close[~mstr_close.index.duplicated(keep="last")]

        btc_hourly = load_crypto("BTC/USDT", pad_start, end, interval="1h")
        btc_daily = _prep(btc_hourly)["close"].resample("1D").last().dropna()
        btc_daily.index = _to_naive_daily(btc_daily.index)
        btc_daily = btc_daily[~btc_daily.index.duplicated(keep="last")]

        common = mstr_close.index.union(btc_daily.index)
        mstr_aligned = mstr_close.reindex(common).ffill()
        btc_aligned = btc_daily.reindex(common).ffill()
        ratio = (mstr_aligned / btc_aligned).dropna()
        ratio_sma = ratio.rolling(ratio_sma_window).mean()
        gate = (ratio > ratio_sma).astype(int)
        _ratio_cache[cache_key] = gate

    idx_naive = _to_naive_daily(index)
    reindexed = gate.reindex(idx_naive, method="ffill").fillna(0).astype(int)
    reindexed.index = index
    return reindexed


def generate_signals(
    price_df: pd.DataFrame,
    trend_sma_window: int = 100,
    ratio_sma_window: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long when close > own trend_sma_window-day SMA AND the MSTR/BTC ratio
    ("mNAV proxy") is above its own ratio_sma_window-day SMA (mNAV
    expanding -- bitcoin-market risk-on proxy); flat otherwise.
    """
    df = _prep(price_df)
    close = df["close"]

    own_sma = close.rolling(trend_sma_window).mean()
    own_trend_up = close > own_sma

    ratio_gate = _load_mnav_gate(df.index, ratio_sma_window)

    position = (own_trend_up.astype(int) & ratio_gate).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
