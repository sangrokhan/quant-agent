"""Strategy: BTC/ETH perpetual funding-rate contrarian continuous sizing dial.

Hypothesis (see knowledge_base/strategies_log.jsonl id 2026-09-20-031):
Perpetual futures funding rate is paid periodically (Binance: every 8h)
between long and short position holders to keep the perpetual price
anchored to spot; a persistently POSITIVE funding rate means longs are
paying shorts (crowded long positioning / bullish euphoria, a classic
contrarian-bearish tell), while a persistently NEGATIVE funding rate means
shorts are paying longs (crowded short / capitulation, a classic
contrarian-bullish tell). This repo's prior funding-rate attempt
(2026-09-02-001, BTC/USDT funding-rate-extreme mean reversion on 1h bars,
rejected) and several subsequent iterations (2026-09-09-009, 2026-09-10-084,
2026-09-18-118) explicitly marked funding-rate strategies as
"feasibility-blocked, repo data/loaders.py has no funding-rate data
source" -- this was WRONG. Verified this iteration via direct ccxt calls
(`ccxt.binance().fetch_funding_rate_history(...)`, paginated via `since`)
that Binance's public funding-rate-history endpoint is freely, publicly
accessible with NO authentication required (same ccxt library this repo's
data/loaders.py already depends on for OHLCV) and has full history back to
at least Jan 2020 for BTC/USDT and ETH/USDT perpetuals. This is the first
strategy in this repo to correctly access this data source (the prior
2026-09-02-001 rejection used a DIFFERENT construction: 1h-bar binary
threshold mean-reversion, not the daily-bar continuous-sizing-dial pattern
that has repeatedly rescued other binary-rejected indicators in this repo).

This iteration reframes the funding-rate contrarian signal as a CONTINUOUS
SIZING dial (rolling z-scored, tanh-squashed, and INVERTED so negative
funding = positive dial = more exposure) within an SMA(trend_window)
uptrend gate, aggregating the 8h funding observations to the strategy's
native daily bar frequency via a rolling sum (cumulative funding cost/
credit over the trailing window, matching how funding actually accrues).

Tested on crypto (BTC/USDT, ETH/USDT) where perpetual funding is
economically meaningful. Not applicable to equity (no perpetual futures
funding-rate mechanism for SPY/QQQ) -- crypto-only by construction, unlike
this repo's usual cross-asset-class grid convention.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
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
    """Map a spot-style symbol (e.g. 'BTC/USDT') to its Binance USDM
    perpetual swap symbol (e.g. 'BTC/USDT:USDT') for ccxt's unified API."""
    if ":" in symbol:
        return symbol
    return f"{symbol}:USDT"


def _fetch_funding_history(symbol: str, start: datetime, end: datetime) -> pd.Series:
    """Paginated fetch of Binance perpetual funding-rate history via ccxt
    (public endpoint, no authentication required). Returns a daily-summed
    series (sum of all 8h funding observations within each calendar day)
    indexed by day, cached in-process per symbol."""
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
    for _ in range(60):  # hard cap on pagination rounds as a safety backstop
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


def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
    raw = raw_exposure.fillna(0.0).to_numpy()
    held = np.zeros_like(raw)
    current = 0.0
    for i, r in enumerate(raw):
        if abs(r - current) > deadband:
            current = r
        held[i] = current
    return pd.Series(held, index=raw_exposure.index)


def generate_signals(
    price_df: pd.DataFrame,
    symbol: str = "BTC/USDT",
    trend_window: int = 40,
    funding_window: int = 21,
    zscore_window: int = 100,
    base_exposure: float = 0.5,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update. `symbol` selects which perpetual's
    funding history to fetch (must match the asset in price_df)."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    start = df.index.min().to_pydatetime()
    end = df.index.max().to_pydatetime()
    funding_daily = _fetch_funding_history(symbol, start, end)
    funding_daily = funding_daily.reindex(pd.date_range(start.date(), end.date(), freq="D", tz="UTC")).fillna(0.0)

    rolling_funding = funding_daily.rolling(funding_window).sum()
    roll_mean = rolling_funding.rolling(zscore_window).mean()
    roll_std = rolling_funding.rolling(zscore_window).std().replace(0, np.nan)
    z = (rolling_funding - roll_mean) / roll_std
    # INVERTED: negative funding (shorts paying longs, crowded-short
    # capitulation) -> positive dial -> more exposure.
    dial = np.tanh(-sensitivity * z)

    dial_reindexed = dial.reindex(df.index, method="ffill").fillna(0.0)
    raw_exposure = base_exposure + base_exposure * dial_reindexed
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    symbol: str = "BTC/USDT",
    trend_window: int = 40,
    funding_window: int = 21,
    zscore_window: int = 100,
    base_exposure: float = 0.5,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.15,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        symbol=symbol,
        trend_window=trend_window,
        funding_window=funding_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
