"""Strategy: Perpetual funding-rate MOMENTUM (rate-of-change) contrarian reversal.

Hypothesis (see knowledge_base/strategies_log.jsonl id 2026-09-26-064):
Per https://www.chelseawelding.com/funding-rate-momentum-reversal-strategy-backtest-results/
(a trading-blog backtest writeup, browser_exec-read after web_extract's DDGS
backend refused non-search extraction): the funding-rate MOMENTUM (the
rolling rate-of-change of the funding rate itself over a short window, "like
using RSI on funding data") signals crowd-conviction extremes better than
the raw funding LEVEL or a static z-score of the level. The source claims a
3-period rate-of-change of hourly funding exceeding +/-0.08% predicts a
short-term reversal, entered counter to the funding-momentum direction
(extreme positive funding ROC = crowded/over-extended longs = fade short;
extreme negative funding ROC = capitulating shorts = fade long).

This is DISTINCT from every other funding-rate construction already in this
KB: 2026-09-02-001 (1h absolute-level threshold), 2026-09-20-031 (rolling-sum
z-score continuous contrarian sizing dial on the LEVEL), 2026-09-20-035
(trend-confirmation AND-gate on the LEVEL), 2026-09-20-036 (z-score spike
mean reversion on the daily-MIN LEVEL), 2026-09-23-143 (funding-vs-price
DIVERGENCE state machine). None of those construct a rate-of-change
(momentum/derivative) of the funding series itself -- this iteration adapts
that specific mechanic to this repo's daily-bar cadence: funding is
daily-summed (matching 2026-09-20-031's convention for how funding actually
accrues), then a short-window rate-of-change of that daily-summed series is
z-scored (adapting the source's fixed +/-0.08%/hr threshold, which doesn't
transfer directly to a daily-summed series, into a self-calibrating
statistical threshold as this repo's convention already established for the
LEVEL-based 2026-09-20-036 z-score construction) to flag extreme momentum
bursts, faded with a fixed-day hold.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({-1,0,1} position series)
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

_funding_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _ccxt_symbol_for_perp(symbol: str) -> str:
    if ":" in symbol:
        return symbol
    return f"{symbol}:USDT"


def _fetch_funding_history(symbol: str, start: datetime, end: datetime) -> pd.Series:
    """Paginated fetch of Binance perpetual funding-rate history via ccxt
    (public endpoint, no authentication required). Returns a daily-SUMMED
    series (matching 2026-09-20-031's convention for accrued funding cost),
    cached in-process per symbol."""
    cache_key = symbol
    if cache_key in _funding_cache:
        return _funding_cache[cache_key]

    import ccxt

    ex = ccxt.binance()
    perp_symbol = _ccxt_symbol_for_perp(symbol)
    since_ms = int(start.replace(tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(end.replace(tzinfo=timezone.utc).timestamp() * 1000)

    all_records = []
    cursor = since_ms
    for _ in range(60):
        try:
            batch = ex.fetch_funding_rate_history(perp_symbol, since=cursor, limit=1000)
        except Exception:
            break
        if not batch:
            break
        all_records.extend(batch)
        last_ts = batch[-1]["timestamp"]
        if last_ts <= cursor or last_ts >= end_ms:
            break
        cursor = last_ts + 1
        time.sleep(0.15)

    if not all_records:
        idx = pd.date_range(start, end, freq="D", tz="UTC")
        series = pd.Series(0.0, index=idx)
        _funding_cache[cache_key] = series
        return series

    idx = pd.to_datetime([r["timestamp"] for r in all_records], unit="ms", utc=True)
    rates = pd.Series([r["fundingRate"] for r in all_records], index=idx).sort_index()
    daily_sum = rates.groupby(rates.index.normalize()).sum()
    _funding_cache[cache_key] = daily_sum
    return daily_sum


def generate_signals(
    price_df: pd.DataFrame,
    symbol: str = "BTC/USDT",
    roc_window: int = 3,
    zscore_window: int = 60,
    momentum_zscore_threshold: float = 2.0,
    max_hold_days: int = 4,
) -> pd.Series:
    """Return a {-1,0,1} position series.

    Entry: the `roc_window`-day rate-of-change of the daily-summed funding
    rate z-scores (over `zscore_window`) beyond +/-`momentum_zscore_threshold`
    -- a statistically extreme BURST in funding momentum, in either
    direction. Fade it: extreme positive funding momentum (crowded longs
    accelerating) -> short; extreme negative funding momentum (capitulating
    shorts accelerating) -> long. Exit: fixed `max_hold_days` time-stop (the
    source's reversal window is short-lived, 48h on hourly bars).
    """
    df = _prep(price_df)
    close = df["close"]

    start = df.index.min().to_pydatetime()
    end = df.index.max().to_pydatetime()
    funding_daily = _fetch_funding_history(symbol, start, end)
    funding_daily = funding_daily.reindex(
        pd.date_range(start.date(), end.date(), freq="D", tz="UTC")
    ).fillna(0.0)

    funding_roc = funding_daily.diff(roc_window)
    roll_mean = funding_roc.rolling(zscore_window).mean()
    roll_std = funding_roc.rolling(zscore_window).std().replace(0, np.nan)
    z = (funding_roc - roll_mean) / roll_std

    long_signal = (z < -momentum_zscore_threshold).reindex(df.index, method="ffill").fillna(False)
    short_signal = (z > momentum_zscore_threshold).reindex(df.index, method="ffill").fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    direction = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if held >= max_hold_days:
                in_position = False
                direction = 0
                position.iloc[i] = 0
                continue
            position.iloc[i] = direction
        else:
            if bool(long_signal.iloc[i]):
                in_position = True
                direction = 1
                entry_idx = i
                position.iloc[i] = 1
            elif bool(short_signal.iloc[i]):
                in_position = True
                direction = -1
                entry_idx = i
                position.iloc[i] = -1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
