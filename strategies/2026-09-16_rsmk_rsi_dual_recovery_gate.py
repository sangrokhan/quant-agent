"""Strategy: Katsanos RSMK relative-strength turn-up + RSI oversold-recovery
dual-filter entry (TASC October 2026 Traders' Tips, WealthLab implementation
of Markos Katsanos' "A Low-Risk ETF Trading Strategy"), with profit-target/
time-stop/RSMK-collapse exits, adapted from a multi-ETF rotation system to a
single-asset-vs-benchmark long/flat signal.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per https://traders.com/documentation/feedbk_docs/2026/10/traderstips.html
(visited this iteration via browser_exec -- web_search DDGS backend
RequestError/TLS-close-notify on every query attempted), Katsanos' "Low-Risk
ETF Trading Strategy" article combines TWO independent momentum-recovery
filters that must agree before entry: (1) RSMK (his own relative-strength-
vs-benchmark oscillator, already in this repo from 2026-09-12-153 as a
standalone MACD-style signal-line crossover, REJECTED there) must be
freshly turning UP from a recent low (RSMK > its own MA, RSMK > its own
3-bar high one bar ago, RSMK > a small positive threshold, but RSMK < 25 so
not yet overextended) -- i.e. relative strength just starting a NEW
uptrend, not already in one; (2) short-period RSI must show the classic
oversold-then-recovering pattern (been below rsi_oversold within the last
20 bars, now turning up off its own 2-bar high). A short-term EMA(5)>SMA
trend confirmation gates the entry further. Exit on RSMK collapsing below
-threshold, a max-hold-days time-stop, or a profit target. This tests
whether RSMK's ALREADY-REJECTED standalone signal becomes viable when
combined with the RSI oversold-recovery AND-gate the source paper actually
uses (the repo's prior 2026-09-12-153 attempt used RSMK stand-alone,
without this confirmation). First RSMK+RSI dual-momentum-recovery
AND-gated entry system in this repo; benchmark defaults to SPY for equity
symbols and BTC/USDT for crypto symbols (fetched internally, same pattern
as strategies/2026-09-08_pairs_zscore_cointegration.py).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position).
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_benchmark(index: pd.DatetimeIndex, asset_class: str, benchmark_symbol: str) -> pd.Series:
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity, load_crypto  # noqa: E402

    start = index.min()
    end = index.max() + timedelta(days=2)
    if asset_class == "crypto":
        bench_df = load_crypto(benchmark_symbol, start, end)
    else:
        bench_df = load_equity(benchmark_symbol, start, end)
    bench_df = _prep(bench_df)
    return bench_df["close"]


def _rsi(close: pd.Series, length: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - 100.0 / (1.0 + rs)
    return rsi.fillna(50.0)


def _rsmk(close: pd.Series, benchmark: pd.Series, period: int = 35, smooth: int = 3) -> pd.Series:
    """Katsanos RSMK: EMA(period-bar momentum of log(asset/benchmark)) * 100."""
    ratio = np.log(close / benchmark.reindex(close.index).ffill())
    mom = ratio - ratio.shift(period)
    rsmk = mom.ewm(span=smooth, adjust=False).mean() * 100.0
    return rsmk


def generate_signals(
    price_df: pd.DataFrame,
    asset_class: str = "equity",
    benchmark_symbol: str = "SPY",
    rs_period: int = 35,
    rs_smooth: int = 3,
    rsmk_ma_window: int = 60,
    rsmk_turn_lookback: int = 3,
    rscrit: float = 2.0,
    rsmk_overext: float = 25.0,
    rsi_length: int = 6,
    rsi_oversold: float = 35.0,
    rsi_oversold_lookback: int = 20,
    ema_fast: int = 5,
    sma_confirm: int = 15,
    time_exit: int = 30,
    profit_target: float = 0.10,
) -> pd.Series:
    """Return a 0/1 long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    benchmark = _load_benchmark(df.index, asset_class, benchmark_symbol)

    rsmk = _rsmk(close, benchmark, period=rs_period, smooth=rs_smooth)
    rsmk_ma = rsmk.rolling(rsmk_ma_window).mean()
    rsmk_turn_up = rsmk > rsmk.shift(1).rolling(rsmk_turn_lookback).max()

    rsi = _rsi(close, rsi_length)
    rsi_recent_oversold = rsi.rolling(rsi_oversold_lookback).min() < rsi_oversold
    rsi_turn_up = rsi > rsi.shift(1).rolling(2).max()

    ema5 = close.ewm(span=ema_fast, adjust=False).mean()
    sma_conf = close.rolling(sma_confirm).mean()
    trend_confirm = ema5 > sma_conf.shift(5)

    entry_cond = (
        (rsmk > rsmk_ma)
        & rsmk_turn_up
        & (rsmk > rscrit)
        & (rsmk < rsmk_overext)
        & rsi_recent_oversold
        & rsi_turn_up
        & trend_confirm
    ).fillna(False)

    exit_collapse = (rsmk < -rscrit).fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_days = 0
    entry_price = None
    for i, ts in enumerate(df.index):
        px = close.iloc[i]
        if in_position:
            hold_days += 1
            hit_target = entry_price is not None and px >= entry_price * (1.0 + profit_target)
            if exit_collapse.iloc[i] or hold_days >= time_exit or hit_target:
                in_position = False
                hold_days = 0
                entry_price = None
            else:
                position.iloc[i] = 1
        else:
            if entry_cond.iloc[i]:
                in_position = True
                hold_days = 1
                entry_price = px
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    asset_class: str = "equity",
    benchmark_symbol: str = "SPY",
    rs_period: int = 35,
    rs_smooth: int = 3,
    rsmk_ma_window: int = 60,
    rsmk_turn_lookback: int = 3,
    rscrit: float = 2.0,
    rsmk_overext: float = 25.0,
    rsi_length: int = 6,
    rsi_oversold: float = 35.0,
    rsi_oversold_lookback: int = 20,
    ema_fast: int = 5,
    sma_confirm: int = 15,
    time_exit: int = 30,
    profit_target: float = 0.10,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_returns = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        asset_class=asset_class,
        benchmark_symbol=benchmark_symbol,
        rs_period=rs_period,
        rs_smooth=rs_smooth,
        rsmk_ma_window=rsmk_ma_window,
        rsmk_turn_lookback=rsmk_turn_lookback,
        rscrit=rscrit,
        rsmk_overext=rsmk_overext,
        rsi_length=rsi_length,
        rsi_oversold=rsi_oversold,
        rsi_oversold_lookback=rsi_oversold_lookback,
        ema_fast=ema_fast,
        sma_confirm=sma_confirm,
        time_exit=time_exit,
        profit_target=profit_target,
    )
    strat_returns = daily_returns * position.shift(1).fillna(0)
    return strat_returns
