"""Strategy: RSMK relative-strength pullback-in-uptrend (Markos Katsanos,
TASC October 2026 "A Low-Risk ETF Trading Strategy").

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-137):
Per https://traders.com/Documentation/FEEDbk_docs/2026/10/TradersTips.html
(Python Traders' Tips code by Rajeev Jain, read via browser_exec after
web_search DDGS backend errored "No results found" this iteration), the
source strategy buys an ETF only when it is in a strong RELATIVE-STRENGTH
uptrend vs a benchmark (RSMK, Katsanos' own indicator, TASC March 2020) that
has just cooled off (RSI pulling back but not yet washed out), combined with
a short-term absolute-price trend confirmation and a market-regime filter
(benchmark 6-day ROC + rolling correlation). This repo simplifies the
source's full multi-ETF scanner (which loops over ~48 sector/country/
commodity ETFs and a correlation-based market-risk gate requiring
cross-sectional data this repo's loaders don't support) down to a
single-symbol version usable with the existing generate_signals/
generate_returns(price_df, **params) contract: the symbol is the candidate
asset, the fetched SPY series is the benchmark for equities (or the
symbol's own asset for crypto using BTC/USDT as benchmark, since crypto has
no natural "market ETF" analog available via ccxt).

This is a genuinely new construction in this repo: RSMK (relative strength
vs benchmark, already tested 3x here -- 2026-09-09-066 VPN, 2026-09-12-153
signal-line crossover, both rejected) is here combined for the FIRST time
with an RSI(10) PULLBACK filter (buy when RSI dipped below 35 in the last
20 bars and has started recovering, i.e. dip-buying strength during a
pullback rather than a raw crossover) and a short-EMA-above-lagged-SMA
absolute trend confirmation -- distinct from both prior RSMK entries (which
used unconditional RSMK crossovers, no pullback/RSI gating).

Signal logic (per source, adapted to single-symbol + benchmark contract)
--------------------------------------------------------------------
- RSMK = EMA(log(close/benchmark_close) - log(close/benchmark_close).shift(rs_bars), rsmk_ema) * 100
- RSMK is in an uptrend: RSMK > its own 50-day MA, RSMK > rsmk_min, and RSMK
  is at/near its own 4-day rolling max (source's own disclosed rule).
- RSI(10) pullback: RSI's 20-day rolling min < rsi_oversold (dipped into
  oversold recently) AND RSI has started recovering (RSI >= RSI 2 bars ago).
- RSMK not yet overbought/extended: RSMK < rsmk_overbought (source's own
  disclosed upper bound, avoids buying an already-extended relative-strength
  spike).
- Short-term absolute trend confirmation: 5-day EMA of close > 15-day SMA of
  close, lagged 5 days (source's own disclosed rule).
- Long entry when ALL of the above hold simultaneously; exit after
  max_hold_days (source doesn't disclose an explicit sell rule -- "reader can
  add sell logic" -- so this repo applies its own standard time-stop) OR
  when RSMK crosses back below its own 50-day MA (trend-loss exit).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import pandas as pd

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity, load_crypto  # noqa: E402

_bench_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def _rsi(close: pd.Series, window: int = 10) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _get_benchmark_close(start: pd.Timestamp, end: pd.Timestamp, is_crypto: bool) -> pd.Series:
    """Fetch benchmark close series (SPY for equities, BTC/USDT for crypto)."""
    key = (start.date().isoformat(), end.date().isoformat(), is_crypto)
    if key in _bench_cache:
        return _bench_cache[key]
    if is_crypto:
        bdf = load_crypto("BTC/USDT", start=start.to_pydatetime(), end=end.to_pydatetime(), interval="1d")
    else:
        bdf = load_equity("SPY", start=start.to_pydatetime(), end=end.to_pydatetime())
    bdf = _prep(bdf)
    ser = bdf["close"]
    _bench_cache[key] = ser
    return ser


def _compute_indicators(price_df: pd.DataFrame, rs_bars: int, rsmk_ema: int) -> pd.DataFrame:
    df = _prep(price_df)
    close = df["close"]

    is_crypto = close.median() < 1  # heuristic guard, unused; determine via symbol context below
    # Determine crypto-ness from typical BTC/ETH price scale isn't reliable; instead detect
    # via presence of a "symbol" attr if provided, else default to equity benchmark (SPY).
    is_crypto = bool(getattr(price_df, "attrs", {}).get("is_crypto", False))

    start = close.index.min()
    end = close.index.max()
    bench_close = _get_benchmark_close(start, end, is_crypto)
    bench_close = bench_close.reindex(close.index).ffill()

    rs = (close / bench_close).apply(lambda x: x)
    import numpy as np

    log_rs = pd.Series(np.log(close.values / bench_close.values), index=close.index)
    rs1 = log_rs - log_rs.shift(rs_bars)
    df["rsmk"] = rs1.ewm(span=rsmk_ema, adjust=False).mean() * 100
    df["rsmk_ma"] = df["rsmk"].rolling(50).mean()
    df["rsi"] = _rsi(close, 10)
    df["trend_ema"] = close.ewm(span=5, adjust=False).mean()
    df["trend_sma"] = close.rolling(15).mean()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    rs_bars: int = 35,
    rsmk_ema: int = 4,
    rsmk_min: float = 3.0,
    rsmk_overbought: float = 25.0,
    rsi_oversold: float = 35.0,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _compute_indicators(price_df, rs_bars, rsmk_ema)

    cond_rs_uptrend = (
        (df["rsmk"] > df["rsmk_ma"])
        & (df["rsmk"] > rsmk_min)
        & (df["rsmk"] >= df["rsmk"].rolling(4).max())
    )
    cond_pullback = (df["rsi"].rolling(20).min() < rsi_oversold) & (df["rsi"] >= df["rsi"].shift(2))
    cond_not_overbought = df["rsmk"] < rsmk_overbought
    cond_trend_confirm = df["trend_ema"] > df["trend_sma"].shift(5)

    cond_buy = cond_rs_uptrend & cond_pullback & cond_not_overbought & cond_trend_confirm
    cond_buy = cond_buy.fillna(False)

    exit_trend_loss = (df["rsmk"] < df["rsmk_ma"]).fillna(False)

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_bars = 0
    for i in range(n):
        if in_pos:
            hold_bars += 1
            if exit_trend_loss.iloc[i] or hold_bars >= max_hold_days:
                in_pos = False
                hold_bars = 0
            else:
                position.iloc[i] = 1
        else:
            if cond_buy.iloc[i]:
                in_pos = True
                hold_bars = 0
                position.iloc[i] = 1
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    # trade next-bar (avoid lookahead): shift position by 1 bar
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
