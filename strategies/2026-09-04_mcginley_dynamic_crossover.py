"""Strategy: Fast/Slow McGinley Dynamic crossover, long-only trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-127):
The McGinley Dynamic (John R. McGinley, 1990) is an adaptive moving average
designed to minimize lag: MD_t = MD_{t-1} + (Price_t - MD_{t-1}) /
(N * (Price_t / MD_{t-1})^4). Because the (Price/MD)^4 term causes the
indicator to speed up in fast/volatile markets and slow down in calm ones,
it's claimed (per fxopen.com's trading guide) to produce fewer false
crossover signals than a comparable SMA/EMA crossover. Standard trading
rule: a fast-period McGinley Dynamic crossing above a slow-period McGinley
Dynamic is bullish (long entry); crossing back below is bearish (exit).
First McGinley Dynamic strategy tested in this repo -- novel indicator
family, distinct from every prior moving-average-crossover variant (SMA/EMA/
HMA/ZLEMA) due to its adaptive, price-ratio-driven step size.

Signal logic
------------
- fast_md = McGinley Dynamic(fast_n), slow_md = McGinley Dynamic(slow_n).
- Entry (long): fast_md crosses above slow_md (today fast>slow, yesterday
  fast<=slow).
- Exit: fast_md crosses back below slow_md, OR max_hold_days elapses.
- Long-only, flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _mcginley_dynamic(price: pd.Series, n: int) -> pd.Series:
    values = np.empty(len(price))
    values[:] = np.nan
    price_vals = price.values
    # Seed with an SMA(n) once we have enough data, then iterate the recursive formula.
    seeded = False
    md_prev = None
    for i in range(len(price_vals)):
        p = price_vals[i]
        if not seeded:
            if i + 1 >= n:
                md_prev = float(np.mean(price_vals[i + 1 - n : i + 1]))
                values[i] = md_prev
                seeded = True
            continue
        if md_prev is None or md_prev == 0 or p is None or np.isnan(p):
            values[i] = md_prev
            continue
        ratio = p / md_prev
        denom = n * (ratio ** 4)
        if denom == 0 or np.isnan(denom) or np.isinf(denom):
            md = md_prev
        else:
            md = md_prev + (p - md_prev) / denom
        values[i] = md
        md_prev = md
    return pd.Series(values, index=price.index)


def generate_signals(
    price_df: pd.DataFrame,
    fast_n: int = 10,
    slow_n: int = 30,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fast_md = _mcginley_dynamic(close, fast_n)
    slow_md = _mcginley_dynamic(close, slow_n)

    cross_up = (fast_md > slow_md) & (fast_md.shift(1) <= slow_md.shift(1))
    cross_down = (fast_md < slow_md) & (fast_md.shift(1) >= slow_md.shift(1))

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_now = bool(cross_down.iloc[i]) if pd.notna(cross_down.iloc[i]) else False
            if exit_now or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            entry_now = bool(cross_up.iloc[i]) if pd.notna(cross_up.iloc[i]) else False
            if entry_now:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    fast_n: int = 10,
    slow_n: int = 30,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(df, fast_n=fast_n, slow_n=slow_n, max_hold_days=max_hold_days)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
