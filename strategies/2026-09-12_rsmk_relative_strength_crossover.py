"""Strategy: RSMK (Relative Strength, Markos Katsanos) signal-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-12-153):
Per Markos Katsanos, TASC March 2020 Traders' Tips ("Relative Strength"),
exact formula transcribed from the TradingView Pine Script implementation
at https://www.tradingview.com/script/qhNCXBmL-Relative-Strength-RSMK-Perks/
("Markos Katsanos' Relative Strength (RSMK)"):

    RSMK = EMA( MOM(log(Asset/Index), period), smooth ) * 100
    signalRSMK = EMA(RSMK, signal_period)

where MOM(x, period) = x[t] - x[t-period] (period-bar momentum/difference
of the log price-ratio series), Asset is the traded symbol's close, and
Index is a benchmark's close (source's own defaults: period=90, smooth=3,
signal_period=20). RSMK crossing above its own signal line indicates the
asset is beginning to outperform the benchmark on a relative-strength
basis -- a long entry per the indicator's standard "signal line crossover"
interpretation (same reading convention as MACD/its signal line, which
RSMK's construction deliberately mirrors).

Operationalized here as: long entry when RSMK crosses above signalRSMK;
exit when RSMK crosses back below signalRSMK, or a max_hold_days time-stop.
Benchmark defaults to SPY for equity symbols and BTC/USDT for crypto
symbols (fetched internally via data/loaders.py, same cache-first service
used elsewhere in this repo) -- distinct from the already-tested single-pair
ETH/BTC relative-strength-rotation strategy because RSMK uses a genuinely
different formula (log-ratio momentum, EMA-smoothed, signal-line cross)
rather than a raw ratio/z-score construction, and is the first strategy in
this repo implementing Katsanos' own RSMK indicator specifically.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)

Note: since RSMK inherently needs a second (benchmark) price series,
generate_signals/generate_returns fetch the benchmark internally via
data/loaders.py, keyed off `benchmark_symbol` (default inferred from
whether the traded symbol looks like a crypto pair, i.e. contains "/").
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_benchmark(index: pd.DatetimeIndex, benchmark_symbol: str, is_crypto: bool) -> pd.Series:
    from loaders import load_equity, load_crypto  # noqa: E402

    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()
    if is_crypto:
        bdf = load_crypto(benchmark_symbol, start, end)
    else:
        bdf = load_equity(benchmark_symbol, start, end)
    bdf = _prep(bdf)
    bench_close = bdf["close"].reindex(index).ffill()
    return bench_close


def _ema(series: pd.Series, period: float) -> pd.Series:
    alpha = 2.0 / (max(1.0, period) + 1.0)
    return series.ewm(alpha=alpha, adjust=False).mean()


def _rsmk(asset_close: pd.Series, index_close: pd.Series, period: int, smooth: float, signal_period: int):
    log_ratio = np.log(asset_close / index_close)
    mom = log_ratio - log_ratio.shift(period)
    rsmk = _ema(mom, smooth) * 100.0
    signal = _ema(rsmk, signal_period)
    return rsmk, signal


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 90,
    smooth: float = 3.0,
    signal_period: int = 20,
    benchmark_symbol: str = None,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    # Fallback heuristic: assume equity unless caller explicitly passes a
    # crypto benchmark (grid_test/validation scripts pass benchmark_symbol
    # explicitly per asset class -- "BTC/USDT" for crypto, "SPY" for equity).
    if benchmark_symbol is None:
        benchmark_symbol = "SPY"
    is_crypto = "/" in benchmark_symbol

    bench_close = _load_benchmark(close.index, benchmark_symbol, is_crypto)

    rsmk, signal = _rsmk(close, bench_close, period, smooth, signal_period)

    entry = (rsmk > signal) & (rsmk.shift(1) <= signal.shift(1))
    exit_cross = (rsmk < signal) & (rsmk.shift(1) >= signal.shift(1))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
