"""Strategy: BITO/BTC ratio momentum ("futures-roll-decay proxy") regime
gate on SMA trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-XXX):
Per Yahoo Finance, TrendSpider, Binance Academy, Seeking Alpha, and CoinDesk
explainers (Google SERP snippets, read via browser_exec this iteration --
the initial web_search query returned normal results for this topic, no
fallback needed): BITO (ProShares Bitcoin Strategy ETF) holds CME bitcoin
FUTURES, not spot bitcoin, and structurally underperforms spot BTC over
time because of (1) a 0.95% expense ratio and (2) "roll cost" / "contango
bleed" -- when the futures curve is in contango (front-month futures priced
above spot), BITO systematically sells expiring (cheaper) contracts and
buys the next month's (more expensive) contracts, bleeding value each
monthly roll. Per Yahoo Finance's own disclosed headline number: "Bitcoin
gained 85% over five years while BITO lost 24%" (i.e. structural
underperformance, not noise).

Since the strategy's persistent drag is proportional to the CURRENT
severity of futures contango (which this repo's OHLCV-only loaders cannot
observe directly -- no CME futures curve data source), this strategy uses
the OBSERVABLE consequence as a proxy: the BITO/BTC price ratio's own
RATE OF CHANGE (rolling ROC, not just level). A ratio in a steady/mild
decline reflects the "normal" expense-ratio-driven drag baseline; an
ACCELERATING decline (ROC dropping sharply below its own recent norm)
is hypothesized to reflect a STEEPENING contango regime (more aggressive
roll-cost bleed), historically associated with crowded long
futures-market positioning and elevated near-term pullback/deleveraging
risk in the underlying spot market itself (steep contango = excess
speculative long futures demand pushing the curve up, a sentiment
extreme). Gate: flat on BTC/USDT (or the primary asset) trend-following
whenever the BITO/BTC ratio's rolling ROC drops into its own bottom decile
(steepest-contango-bleed regime); long (SMA-trend-following as usual)
otherwise.

First strategy in this repo to use BITO (a futures-based bitcoin ETF, as
opposed to a spot ETF or the coin itself) as a cross-asset signal source,
and first application of a "structural product-decay rate" concept
(distinct from the already-tested MSTR/BTC mNAV-premium-LEVEL gate,
2026-09-20-040/041, which used a corporate-treasury equity's ratio LEVEL,
not a futures-ETF's ratio's RATE OF CHANGE) as a systematic filter.

Tested on the intended domain (BTC/USDT, ETH/USDT) AND on equity (QQQ, SPY)
as an explicit falsification check.

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

_gate_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df


def _to_naive_daily(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    idx = pd.to_datetime(index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    return idx.normalize()


def _load_roll_decay_gate(
    index: pd.DatetimeIndex,
    roc_window: int,
    decile_lookback: int,
    decile_threshold: float,
) -> pd.Series:
    """Load BITO (equity, futures-ETF) and BTC/USDT (crypto, daily-resampled)
    closes, compute the BITO/BTC ratio's rolling rate-of-change, and gate =
    True (risk-on / long allowed) UNLESS that ROC is currently in its own
    bottom `decile_threshold` quantile over a trailing `decile_lookback`
    window (steepest-contango-bleed regime -> flat). Cached across calls
    within a process."""
    cache_key = (roc_window, decile_lookback, decile_threshold)
    if cache_key in _gate_cache:
        gate = _gate_cache[cache_key]
    else:
        from loaders import load_equity, load_crypto

        start = index.min().to_pydatetime() if len(index) else datetime(2021, 10, 1)
        end = index.max().to_pydatetime() if len(index) else datetime(2026, 9, 1)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        pad_start = start.replace(year=max(start.year - 1, 2021))

        bito_raw = _prep(load_equity("BITO", pad_start, end))["close"]
        bito_close = bito_raw.copy()
        bito_close.index = _to_naive_daily(bito_close.index)
        bito_close = bito_close[~bito_close.index.duplicated(keep="last")]

        btc_hourly = load_crypto("BTC/USDT", pad_start, end, interval="1h")
        btc_daily = _prep(btc_hourly)["close"].resample("1D").last().dropna()
        btc_daily.index = _to_naive_daily(btc_daily.index)
        btc_daily = btc_daily[~btc_daily.index.duplicated(keep="last")]

        common = bito_close.index.union(btc_daily.index)
        bito_aligned = bito_close.reindex(common).ffill()
        btc_aligned = btc_daily.reindex(common).ffill()
        ratio = (bito_aligned / btc_aligned).dropna()

        roc = ratio.pct_change(roc_window)
        rolling_decile = roc.rolling(decile_lookback).quantile(decile_threshold)
        gate = (roc >= rolling_decile).astype(int)
        _gate_cache[cache_key] = gate

    idx_naive = _to_naive_daily(index)
    reindexed = gate.reindex(idx_naive, method="ffill").fillna(1).astype(int)
    reindexed.index = index
    return reindexed


def generate_signals(
    price_df: pd.DataFrame,
    trend_sma_window: int = 100,
    roc_window: int = 20,
    decile_lookback: int = 180,
    decile_threshold: float = 0.15,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long when close > own trend_sma_window-day SMA AND the BITO/BTC ratio's
    rolling ROC is NOT in its own bottom decile_threshold quantile over the
    trailing decile_lookback window (i.e. futures-roll-decay is not
    currently steepening/accelerating); flat otherwise.
    """
    df = _prep(price_df)
    close = df["close"]

    own_sma = close.rolling(trend_sma_window).mean()
    own_trend_up = close > own_sma

    decay_gate = _load_roll_decay_gate(df.index, roc_window, decile_lookback, decile_threshold)

    position = (own_trend_up.astype(int) & decay_gate).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
