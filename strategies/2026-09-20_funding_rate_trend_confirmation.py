"""Strategy: Perpetual funding-rate TREND-CONFIRMATION gate (not contrarian).

Hypothesis (see knowledge_base/strategies_log.jsonl id 2026-09-20-035):
Direct economic counter-hypothesis to this cron trigger's own
2026-09-20-031 (funding-rate CONTRARIAN sizing dial, accepted -- treats
positive funding as crowded-long/bearish-tell). This iteration tests the
OPPOSITE economic framing: sustained POSITIVE funding rate (longs paying
shorts persistently, not just a single-bar spike) can also be read as
genuine, durable bullish conviction rather than pure crowding -- i.e. as a
TREND-CONFIRMATION filter layered on top of a price-momentum signal, in
the same way this repo's existing ADX/trend-strength gates confirm SMA
crossovers (rather than fade them). Concretely: go long only when BOTH (1)
close > SMA(trend_window) (standard uptrend gate, same convention as this
repo's other trend-following strategies) AND (2) the rolling-summed
funding rate over the trailing window is POSITIVE (the market has been
persistently paying a long-side premium, confirming the trend has genuine
positioning conviction behind it, not just price momentum alone). This is
a binary AND-gate construction, deliberately distinct from 2026-09-20-031's
continuous INVERTED sizing dial -- testing whether the funding-rate signal
has predictive value in the confirmation direction as well as (or instead
of) the contrarian direction already found to work.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position series)
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

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
    trend_window: int = 40,
    funding_window: int = 21,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a {0, leverage_cap} long/flat position series.

    Long only when close > SMA(trend_window) AND the rolling-summed
    funding rate over `funding_window` days is strictly positive
    (sustained long-side premium confirming trend conviction).
    `leverage_cap` scales the ON-position size (still a binary gate, not a
    continuous dial) to allow drawdown control via reduced position size,
    matching this repo's convention for crypto risk retuning.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    start = df.index.min().to_pydatetime()
    end = df.index.max().to_pydatetime()
    funding_daily = _fetch_funding_history(symbol, start, end)
    funding_daily = funding_daily.reindex(pd.date_range(start.date(), end.date(), freq="D", tz="UTC")).fillna(0.0)
    rolling_funding = funding_daily.rolling(funding_window).sum()
    funding_confirms = (rolling_funding > 0).reindex(df.index, method="ffill").fillna(False)

    position = (trend_long.fillna(False) & funding_confirms).astype(float) * leverage_cap
    return position


def generate_returns(
    price_df: pd.DataFrame,
    symbol: str = "BTC/USDT",
    trend_window: int = 40,
    funding_window: int = 21,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df, symbol=symbol, trend_window=trend_window,
        funding_window=funding_window, leverage_cap=leverage_cap,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
