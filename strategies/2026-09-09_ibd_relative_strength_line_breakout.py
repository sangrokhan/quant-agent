"""Strategy: IBD-style Relative Strength Line breakout confirmation (long).

Hypothesis (this iteration):
Per https://www.investors.com/how-to-invest/investors-corner/growth-stocks-breakout-specialty-tool-relative-strength-line/,
IBD's "Relative Strength (RS) Line" is a stock's price divided by a broad
benchmark index (S&P 500), plotted as its own line. The source's own
concrete, repeatedly-illustrated rule: "You'd like to see a relative
strength line making new highs as a stock breaks out, or even before a
breakout... the RS line had already taken new highs [before/as] the stock
broke out past its entry point." I.e. a genuine price breakout (new
N-day high) is a HIGHER-CONVICTION long entry when CONFIRMED by the
RS line (price / benchmark) also making a new N-day high around the same
time -- versus a breakout where relative strength vs the benchmark is NOT
also at a high (the source's counter-example: "the RS line is not
actually seizing new highs at the breakout... but the direction can be an
important indicator").

This is the first cross-asset RELATIVE-STRENGTH-LINE-AS-BREAKOUT-FILTER
strategy in this repo (distinct from the already-tested SPY/QQQ ratio
z-score pairs-trade [2026-09-04-098], SPY/TLT ratio regime filter
[2026-09-05-036], and XLU/SPY beta-rotation regime filter
[2026-09-05-067] -- all of those trade the RATIO ITSELF or use it purely
as a binary risk-on/off gate; this strategy instead uses the ratio's own
rolling-high status as a CONFIRMATION FILTER on top of price's own
independent Donchian-style breakout, exactly matching IBD's stated
"breakout confirmed by RS line making new highs" rule).

For equity: trade QQQ with SPY as the broad-market benchmark (source's
own S&P 500 benchmark choice). For crypto: trade ETH/USDT with BTC/USDT
as benchmark (BTC is the closest crypto analog to a "broad market index").

Signal logic
------------
- price_high_lookback-day Donchian breakout: close crosses above its own
  rolling price_high_lookback-day high (excluding today).
- RS line = close / benchmark_close.
- RS_high_lookback-day RS breakout: RS line is at/near (within
  rs_tolerance_pct of) its own rolling rs_high_lookback-day high.
- Entry (long): price breakout AND RS-line confirmation both true on the
  same bar (or RS confirmation within rs_confirm_window bars before/after
  the price breakout, per source's "before a breakout... or even as it
  breaks out" flexibility).
- Exit: close crosses below a trailing exit_lookback-day low (Donchian-
  style trailing stop, source's own "break below its 10-week moving
  average" topping-behavior analog approximated here with a price-based
  trailing low since a fixed weekly MA isn't part of the loaders'
  daily-bar interface) OR a max_hold_days time-stop.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)

NOTE: unlike every other strategy file in this repo, this one needs a
SECOND (benchmark) price series. Since grid_test.py's run_strategy_grid
only passes a single symbol's price_df per cell, the benchmark series is
fetched internally via data/loaders.py using a module-level BENCHMARK_MAP
keyed by the primary symbol (QQQ->SPY, SPY->QQQ, ETH/USDT->BTC/USDT,
BTC/USDT->ETH/USDT) -- this keeps the generate_signals/generate_returns
keyword-args contract intact while still being a genuine cross-asset
relative-strength signal.

Sources:
    https://www.investors.com/how-to-invest/investors-corner/growth-stocks-breakout-specialty-tool-relative-strength-line/
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity, load_crypto  # noqa: E402

BENCHMARK_MAP = {
    "QQQ": ("SPY", load_equity),
    "SPY": ("QQQ", load_equity),
    "ETH/USDT": ("BTC/USDT", load_crypto),
    "BTC/USDT": ("ETH/USDT", load_crypto),
}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_benchmark(price_df: pd.DataFrame, symbol_hint: str) -> pd.Series:
    """Load a benchmark close series aligned to price_df's index."""
    if symbol_hint not in BENCHMARK_MAP:
        raise ValueError(
            f"No benchmark configured for symbol '{symbol_hint}'. "
            f"Known symbols: {list(BENCHMARK_MAP.keys())}"
        )
    bench_symbol, loader_fn = BENCHMARK_MAP[symbol_hint]
    df = _prep(price_df)
    start = df.index.min().to_pydatetime()
    end = df.index.max().to_pydatetime()
    bench_df = _prep(loader_fn(bench_symbol, start, end))
    bench_close = bench_df["close"].reindex(df.index).ffill().bfill()
    return bench_close


def generate_signals(
    price_df: pd.DataFrame,
    symbol_hint: str = "QQQ",
    price_high_lookback: int = 50,
    rs_high_lookback: int = 50,
    rs_tolerance_pct: float = 0.02,
    rs_confirm_window: int = 10,
    exit_lookback: int = 20,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    bench_close = _load_benchmark(price_df, symbol_hint)
    rs_line = close / bench_close.replace(0, np.nan)

    # Price breakout: close > rolling max of close over the prior window
    # (excluding today).
    price_roll_high = close.shift(1).rolling(price_high_lookback).max()
    price_breakout = (close > price_roll_high).fillna(False)

    # RS-line confirmation: RS line within rs_tolerance_pct of its own
    # rolling high at any point in the +/- rs_confirm_window around today.
    rs_roll_high = rs_line.rolling(rs_high_lookback).max()
    rs_near_high = (rs_line >= rs_roll_high * (1 - rs_tolerance_pct)).fillna(False)
    rs_confirm_any = rs_near_high.rolling(rs_confirm_window * 2 + 1, center=True, min_periods=1).max().astype(bool)

    entry_cond = (price_breakout & rs_confirm_any).fillna(False)

    exit_roll_low = close.shift(1).rolling(exit_lookback).min()
    exit_cond_static = (close < exit_roll_low).fillna(False)

    c = close.to_numpy(dtype=float)
    entry_arr = entry_cond.to_numpy(dtype=bool)
    exit_arr = exit_cond_static.to_numpy(dtype=bool)

    position = np.zeros(n, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if exit_arr[i] or held >= max_hold_days:
                in_position = False
                position[i] = 0
                continue
            position[i] = 1
        else:
            if entry_arr[i]:
                in_position = True
                entry_idx = i
                position[i] = 1
            else:
                position[i] = 0

    return pd.Series(position, index=close.index, dtype=int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
