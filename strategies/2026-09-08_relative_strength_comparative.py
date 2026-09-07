"""Strategy: Relative Strength Comparative (RSC) vs benchmark, MA-cross momentum.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-123):
Per https://www.quantifiedstrategies.com/relative-strength-comparative/,
the Relative Strength Comparative (RSC) indicator divides an asset's price
by a benchmark's price to identify when the asset is outperforming or
underperforming the benchmark -- "used in momentum investing and asset
rotation where it helps in choosing stocks or other assets that have
performed well relative to the whole market." (The source's own specific
Amibroker trading rule is paywalled; this implements the standard/textbook
RSC construction: the asset is in a relative-outperformance regime when its
RSC ratio -- asset_close / benchmark_close -- is rising above its own
trailing moving average, and underperforming when below.) Long entry when
RSC crosses above its own N-day SMA (the asset has just started
outperforming the benchmark); exit when RSC crosses back below that SMA
(relative outperformance has faded) or a max-hold time-stop. This is the
first cross-asset relative-strength (ratio-vs-benchmark) strategy in this
repo -- distinct from prior single-instrument momentum/trend strategies
that never reference a second instrument.

Benchmark pairing (since the grid-test harness evaluates one symbol at a
time): QQQ is tested against SPY as benchmark (and vice versa for
completeness), and for crypto ETH/USDT is tested against BTC/USDT as
benchmark (the natural "market" proxy in each asset class). The strategy
fetches the benchmark series itself via ``data/loaders.py`` using the same
date range as the primary ``price_df`` passed in by the grid harness.

Signal logic
------------
- rsc = asset_close / benchmark_close (aligned on common dates).
- rsc_sma = rolling `rsc_window`-day SMA of rsc.
- Entry (long the ASSET, not the benchmark): rsc crosses above rsc_sma.
- Exit: rsc crosses back below rsc_sma, OR max_hold_days elapses.
- Flat otherwise, long-only, one position at a time.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import sys
import os

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_benchmark(price_df: pd.DataFrame, benchmark_symbol: str, asset_class: str) -> pd.Series:
    from loaders import load_equity, load_crypto  # local import to avoid hard dependency at module load

    df = _prep(price_df)
    start = df.index.min().to_pydatetime()
    end = df.index.max().to_pydatetime()
    if asset_class == "crypto":
        bench_df = load_crypto(benchmark_symbol, start, end)
    else:
        bench_df = load_equity(benchmark_symbol, start, end)
    bench_df = _prep(bench_df)
    return bench_df["close"]


def generate_signals(
    price_df: pd.DataFrame,
    benchmark_symbol: str = "SPY",
    asset_class: str = "equity",
    rsc_window: int = 20,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    bench_close = _load_benchmark(price_df, benchmark_symbol, asset_class)
    bench_close = bench_close.reindex(close.index).ffill()

    rsc = close / bench_close
    rsc_sma = rsc.rolling(rsc_window).mean()

    above = rsc > rsc_sma
    entry = above & (~above.shift(1).fillna(False))
    exit_signal = (~above) & (above.shift(1).fillna(False))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
