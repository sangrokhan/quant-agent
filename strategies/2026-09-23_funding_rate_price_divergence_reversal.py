"""Strategy: BTC/ETH perpetual funding-rate vs. price DIVERGENCE reversal.

Hypothesis (see knowledge_base/strategies_log.jsonl for this id):
Per https://www.cryptochainblog.com/bitcoin-analysis/bitcoin-funding-rate-
divergences-2026-reversal-signals (read this iteration via browser_exec,
web_search DDGS backend returned "No results found" on the direct
divergence-backtest query so fell back to browser search): the article's
disclosed step-by-step monitoring technique defines a DIVERGENCE between
Bitcoin's price direction and its perpetual funding-rate direction over the
same lookback window as a reversal signal, distinct from trading the
*absolute level* of funding (already covered by this repo's
2026-09-20-031 contrarian sizing dial and 2026-09-20-035 trend-confirmation
AND-gate):

  - BEARISH divergence: price rising over the lookback window while the
    rolling-summed funding rate is simultaneously FALLING (longs quietly
    de-risking / new shorts creeping in despite the price still going up) ->
    exit to flat (weakening bullish conviction, take-profit/de-risk signal).
  - BULLISH divergence: price falling over the lookback window while the
    rolling-summed funding rate is simultaneously RISING (shorts covering /
    capitulation-selling losing steam even as price makes new lows) -> enter
    long (early capitulation-exhaustion reversal signal).

This is a state-machine (not a re-evaluated-every-bar binary gate): once a
bullish divergence triggers a long entry, the position is held until either
a bearish divergence fires (exit to flat) or `max_hold_days` elapses,
mirroring the source's framing of divergences as discrete "3-7 day"
reversal-precursor events rather than a continuously-recomputed regime
filter. Funding data fetched from Binance's public
`fetch_funding_rate_history` endpoint (no auth required), same access
pattern first established by 2026-09-20-031 in this repo.

Crypto-only by construction (no perpetual funding-rate mechanism for
equities).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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
    (public endpoint, no authentication required). Returns a daily-summed
    series indexed by day, cached in-process per symbol."""
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


def _state_machine(bullish: np.ndarray, bearish: np.ndarray, max_hold_days: int) -> np.ndarray:
    n = len(bullish)
    pos = np.zeros(n)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            if bearish[i] or hold_count >= max_hold_days:
                in_pos = False
                hold_count = 0
            else:
                pos[i] = 1.0
        else:
            if bullish[i]:
                in_pos = True
                hold_count = 0
                pos[i] = 1.0
    return pos


def generate_signals(
    price_df: pd.DataFrame,
    symbol: str = "BTC/USDT",
    divergence_window: int = 10,
    funding_window: int = 21,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a 0/1 position series based on price-vs-funding divergence."""
    df = _prep(price_df)
    close = df["close"]

    start = df.index.min().to_pydatetime()
    end = df.index.max().to_pydatetime()
    funding_daily = _fetch_funding_history(symbol, start, end)
    funding_daily = funding_daily.reindex(
        pd.date_range(start.date(), end.date(), freq="D", tz="UTC")
    ).fillna(0.0)

    rolling_funding = funding_daily.rolling(funding_window).sum()
    rolling_funding_on_price_idx = rolling_funding.reindex(df.index, method="ffill")

    price_change = close.pct_change(divergence_window)
    funding_change = rolling_funding_on_price_idx.diff(divergence_window)

    bullish = ((price_change < 0) & (funding_change > 0)).fillna(False).to_numpy()
    bearish = ((price_change > 0) & (funding_change < 0)).fillna(False).to_numpy()

    pos = _state_machine(bullish, bearish, max_hold_days)
    return pd.Series(pos, index=df.index)


def generate_returns(
    price_df: pd.DataFrame,
    symbol: str = "BTC/USDT",
    divergence_window: int = 10,
    funding_window: int = 21,
    max_hold_days: int = 30,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    signal = generate_signals(
        price_df,
        symbol=symbol,
        divergence_window=divergence_window,
        funding_window=funding_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = signal.shift(1).fillna(0.0) * daily_ret
    return strat_ret
