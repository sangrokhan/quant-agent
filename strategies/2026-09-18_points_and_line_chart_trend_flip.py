"""Strategy: Points & Line (P&L) Chart trend-flip trend-following, gated by
an SMA(trend_window) uptrend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-002):
Per TASC November 2025 Traders' Tips (Mohamed Ashraf and Mohamed Meregy,
"The Points & Line Chart"), fully disclosed EasyLanguage at
https://traders.com/Documentation/FEEDbk_docs/2025/11/TradersTips.html:
a new box size is computed per bar from the CURRENT close price via a
Point-and-Figure-style box-size lookup table (finer boxes for cheap
symbols, coarser for expensive ones), then price is floored to the nearest
box multiple ("BasePrice"). A P&L "point" (plotted line vertex) is only
placed when price advances by >=1 box in the current direction (Dir), or
reverses by >= ReversalAmount boxes against the current direction (source
default ReversalAmount=3) -- otherwise the line stays flat, filtering out
sub-box-size noise entirely (distinct from every ATR/percentage-based
noise filter already tested in this repo, since it uses discrete
Point-and-Figure-style box quantization rather than a continuous
volatility measure). This iteration operationalizes the P&L line's own
directional STATE (Dir: +1 while advancing/holding an up-leg, -1 while
declining) as a discrete state-machine trend signal: long entry when Dir
flips from -1 to +1 (a confirmed new P&L up-leg begins, i.e. the reversal
trigger fired upward), exit when Dir flips back to -1, gated by a longer
SMA(trend_window) filter to avoid trading P&L noise against the larger
trend. First Points & Line Chart-based strategy in this repo -- distinct
from every other box/brick-based construction already tested (Renko,
Kagi, Three-Line-Break, Point-and-Figure double-top breakout) since the
P&L box size here is a DISCRETE LOOKUP TABLE keyed to the symbol's own
price level, not a fixed brick/ATR-derived size.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position series).
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


def _pl_box_size(close: float) -> float:
    """Point-and-Figure-style box-size lookup, per source's disclosed table."""
    if close < 0.25:
        return 0.025
    if close < 0.5:
        return 0.05
    if close < 1:
        return 0.1
    if close < 5:
        return 0.25
    if close < 20:
        return 0.5
    if close < 100:
        return 1.0
    if close < 200:
        return 2.0
    if close < 500:
        return 5.0
    if close < 1000:
        return 10.0
    if close < 2000:
        return 20.0
    if close < 5000:
        return 50.0
    if close < 10000:
        return 100.0
    if close < 20000:
        return 200.0
    return 500.0


def _pl_direction(close: pd.Series, reversal_amount: int) -> pd.Series:
    """Reconstruct the source's P&L chart Dir state machine.

    Dir starts at +1. While Dir==+1: a new point only advances LastPLPrice
    when BasePrice >= LastPLPrice + box (continue up) or flips to Dir=-1
    when Close <= LastPLPrice - box*reversal_amount (reversal down).
    Mirror for Dir==-1. Otherwise Dir/LastPLPrice hold.
    """
    n = len(close)
    dir_state = np.ones(n, dtype=int)
    close_vals = close.to_numpy()

    last_pl_price = None
    cur_dir = 1
    for i in range(n):
        c = close_vals[i]
        box = _pl_box_size(c)
        base_price = np.floor(c / box) * box
        if i == 0:
            last_pl_price = base_price
            cur_dir = 1
            dir_state[i] = cur_dir
            continue
        if cur_dir == 1:
            if base_price >= last_pl_price + box:
                last_pl_price = base_price
            elif c <= last_pl_price - (box * reversal_amount):
                last_pl_price = base_price
                cur_dir = -1
        else:  # cur_dir == -1
            if base_price <= last_pl_price - box:
                last_pl_price = base_price
            elif c >= last_pl_price + (box * reversal_amount):
                last_pl_price = base_price
                cur_dir = 1
        dir_state[i] = cur_dir
    return pd.Series(dir_state, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    reversal_amount: int = 3,
    trend_window: int = 100,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    trend_up = close > close.rolling(trend_window).mean()
    pl_dir = _pl_direction(close, reversal_amount)
    dir_flip_up = (pl_dir == 1) & (pl_dir.shift(1) == -1)
    dir_flip_down = (pl_dir == -1) & (pl_dir.shift(1) == 1)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(dir_flip_down.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(dir_flip_up.iloc[i]) and bool(trend_up.iloc[i]):
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
