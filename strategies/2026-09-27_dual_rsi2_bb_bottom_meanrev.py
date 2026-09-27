"""Strategy: Dual-RSI(2) Bollinger-Band-Bottom Mean Reversion (SPY + market
confirmation), the "simple 4-rule" version described in SetupAlpha's "Why
Simpler Trading Strategies Survive Longer (4 Trading Rules Beat 12 Rules)".

Hypothesis (see knowledge_base/strategies_log.jsonl entry for this
iteration's id): Per SetupAlpha
(https://setup4alpha.substack.com/p/every-rule-you-add-is-a-risk, read via
browser_exec this iteration -- web_search returned only archive-index
snippets, browser_exec used to read the free-preview section directly),
the article's own free-preview section discloses in full the "simple"
4-condition mean-reversion strategy it uses as its baseline (the paid
section only covers the 8 ADDITIONAL over-fit filters, not tested here):
"stocks in an uptrend that pull back hard enough for RSI(2) to drop below
20, while the broader market (SPY) is also pulling back. Entry on a limit
order at the Bollinger Band bottom. Exit when RSI(2) recovers above 70."
The source's own out-of-sample test (2019-2026) found this SIMPLE 4-rule
version's performance IMPROVED out of sample (CAGR 7.18%->11.78%, Sharpe
0.69->1.18, win rate 66.79%->75.80%) while a 12-rule elaborated version
collapsed out of sample -- a novelty-relevant point since this repo has
plenty of single-oscillator-plus-trend-filter strategies, but this
specific THREE-PART combination (primary-asset RSI(2) pullback + a
SEPARATE market-benchmark RSI(2) pullback confirmation + Bollinger Band
lower-touch entry, with a symmetric RSI(2) recovery exit) has not been
tested together in this repo before.

Since this repo's strategy interface operates on a single symbol's own
price_df (no cross-sectional universe), "the stock" and "the broader
market" are adapted to a primary/benchmark PAIR: QQQ (primary) vs SPY
(benchmark) for equity, and ETH/USDT (primary) vs BTC/USDT (benchmark)
for crypto -- a benchmark price series is fetched internally via the same
loader used for the primary symbol (mirroring this repo's existing
cross-asset-signal pattern, e.g. 2026-09-11-072's IEF/GLD/USO stress
signal).

Signal logic
------------
- RSI(2) of the primary asset's close (Wilder-style with SMA seed, per
  Connors' original RSI(2) convention already used elsewhere in this
  repo).
- RSI(2) of the benchmark asset's close (fetched via the SAME loader
  function used for the primary symbol, benchmark_symbol param).
- Bollinger Bands (bb_window, bb_std) on the primary asset's close.
- Entry (long) at close when: primary RSI(2) < rsi_entry AND benchmark
  RSI(2) < rsi_entry AND primary close < lower Bollinger Band (approximates
  the source's "limit order at the Bollinger Band bottom" with a same-bar
  touch condition, since this repo's generate_signals/generate_returns
  interface does not support intrabar limit-order fills).
- Exit (flat) at close when: primary RSI(2) > rsi_exit.
- max_hold_days safety valve (source's own construction implies an
  eventual RSI(2) recovery but this repo's convention always bounds
  worst-case holding period).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position).

NOTE: because the benchmark series must be fetched internally,
generate_signals/generate_returns accept a ``benchmark_loader`` callable
and ``benchmark_symbol``/``benchmark_start``/``benchmark_end`` so the
grid-test harness (which only passes the PRIMARY price_df positionally)
can still call this strategy via its normal **params contract -- the
Research Agent's grid-test driver script supplies these as fixed
(non-swept) params alongside the swept ones.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _get_benchmark_close(
    price_df: pd.DataFrame,
    benchmark_loader: Optional[Callable] = None,
    benchmark_symbol: Optional[str] = None,
) -> Optional[pd.Series]:
    if benchmark_loader is None or benchmark_symbol is None:
        return None
    df = _prep(price_df)
    start = df.index.min()
    end = df.index.max()
    # Loaders accept datetime; index may already be datetime-like.
    start_dt = start.to_pydatetime() if hasattr(start, "to_pydatetime") else start
    end_dt = end.to_pydatetime() if hasattr(end, "to_pydatetime") else end
    try:
        bench_df = benchmark_loader(benchmark_symbol, start_dt, end_dt, interval="1d")
    except TypeError:
        bench_df = benchmark_loader(benchmark_symbol, start_dt, end_dt)
    bench_df = _prep(bench_df)
    bench_close = bench_df["close"].reindex(df.index).ffill()
    return bench_close


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 2,
    rsi_entry: float = 20.0,
    rsi_exit: float = 70.0,
    bb_window: int = 20,
    bb_std: float = 2.0,
    max_hold_days: int = 15,
    benchmark_loader: Optional[Callable] = None,
    benchmark_symbol: Optional[str] = None,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rsi_primary = _rsi(close, rsi_period)

    bench_close = _get_benchmark_close(price_df, benchmark_loader, benchmark_symbol)
    if bench_close is not None:
        rsi_bench = _rsi(bench_close, rsi_period)
        bench_pullback = rsi_bench < rsi_entry
    else:
        # No benchmark supplied -- degrade gracefully to single-asset rule
        # (benchmark condition treated as always-true).
        bench_pullback = pd.Series(True, index=close.index)

    sma = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()
    lower_band = sma - bb_std * std

    entry = (rsi_primary < rsi_entry) & bench_pullback & (close < lower_band)
    exit_signal = rsi_primary > rsi_exit

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]) if pd.notna(entry.iloc[i]) else False:
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
    strategy_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strategy_ret
