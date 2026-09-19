"""Strategy: Perpetual funding-rate EXTREME-NEGATIVE-SPIKE mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id 2026-09-20-036):
Third distinct construction on the now-verified-feasible ccxt funding-rate
data source this cron trigger (after 2026-09-20-031 contrarian continuous
sizing dial and 2026-09-20-035 trend-confirmation AND-gate, both accepted).
This repo's ORIGINAL funding-rate attempt (2026-09-02-001, "BTC/USDT
funding-rate-extreme mean reversion (long when funding < -0.01%, flat
otherwise)") was rejected, but used 1h bars and a static absolute threshold
-- a materially different construction from this iteration. This iteration
retests the SAME underlying economic idea (a single extreme negative
funding print signals acute short-side capitulation, a sharper/more
event-driven trigger than the smoothed rolling-window constructions already
tested) but on daily bars with a rolling z-score threshold (adapting to the
funding rate's own historically-shifting volatility/regime, rather than a
fixed absolute cutoff that may not generalize across the multi-year sample)
and a short fixed-day hold (capitulation bounces are typically short-lived,
per the general "extreme sentiment reversion" pattern already validated
elsewhere in this repo, e.g. CVR1/CVR3 VIX reversals).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position series)
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
    daily_min = rates.groupby(rates.index.normalize()).min()  # most-negative print within the day
    _funding_cache[cache_key] = daily_min
    return daily_min


def generate_signals(
    price_df: pd.DataFrame,
    symbol: str = "BTC/USDT",
    zscore_window: int = 100,
    spike_zscore_threshold: float = -2.0,
    max_hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry: today's minimum intraday funding print is a rolling
    zscore_window-day z-score spike below spike_zscore_threshold (a
    statistically extreme negative funding event relative to the funding
    series' own recent regime, not a fixed absolute cutoff). Exit: fixed
    max_hold_days time-stop (capitulation bounces are typically short-lived).
    """
    df = _prep(price_df)
    close = df["close"]

    start = df.index.min().to_pydatetime()
    end = df.index.max().to_pydatetime()
    funding_daily_min = _fetch_funding_history(symbol, start, end)
    funding_daily_min = funding_daily_min.reindex(
        pd.date_range(start.date(), end.date(), freq="D", tz="UTC")
    ).fillna(0.0)

    roll_mean = funding_daily_min.rolling(zscore_window).mean()
    roll_std = funding_daily_min.rolling(zscore_window).std().replace(0, np.nan)
    z = (funding_daily_min - roll_mean) / roll_std

    spike_signal = (z < spike_zscore_threshold).reindex(df.index, method="ffill").fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(spike_signal.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
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
