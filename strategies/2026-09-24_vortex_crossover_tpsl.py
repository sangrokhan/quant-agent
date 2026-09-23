"""Strategy: Vortex Indicator crossover entry, ATR-based fixed TP:SL exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-014):
Per StrategyVerdict's "Vortex Indicator Strategy Backtest: the Crossover
That Actually Has an Edge (Conditionally)"
(https://strategyverdict.com/vortex-indicator-backtest/), a rigorous
6-axis backtest (Binance BTC/ETH/SOL/BNB/XRP, Jul 2024-Jul 2026) of the
standard Vortex(14) crossover (VI+ crosses above VI- -> long) found the
edge concentrated on higher timeframes (4H/1D -- the source's own "1D"
bucket had the single best net return, +64%) and, distinctly, found a
FIXED TP:SL RATIO exit (not the opposite-crossover exit) robustly
profitable across every ratio tested from 1:1 to 1:5 (profit factor
1.08-1.15, peaking at 1:1.5). This repo has 5 prior Vortex-family entries
(plain SMA-gated crossover, ADX-gated + ATR trailing stop, continuous
sizing dial, Vortex+TSI dual-confirmation, separation-convergence exit)
but NONE used a fixed TP:SL ratio exit -- all used an opposite-crossover,
trailing-stop, or convergence-based exit. This isolates that specific
exit-mechanism finding. Long-only adaptation of source's stop-and-reverse
system per SAFETY.md (drop the short leg; go flat instead of reversing).

Signal logic
------------
- VI+ = sum(|High_t - Low_{t-1}|, vi_period) / sum(True Range, vi_period)
- VI- = sum(|Low_t - High_{t-1}|, vi_period) / sum(True Range, vi_period)
- Entry (long): VI+ crosses above VI- (fresh cross, not just VI+>VI-).
- Exit: ATR(vi_period)-based fixed take-profit / stop-loss bracket set at
  entry -- TP = entry_price + tp_sl_ratio * atr_mult * ATR, SL =
  entry_price - atr_mult * ATR (source's own default risk unit is 1x ATR
  for the stop leg, with the TP leg scaled by tp_sl_ratio). Exit whichever
  level is touched first (checked via daily high/low), or a max_hold_days
  time-stop as a safety net (the source's TP:SL brackets have no time
  limit, but this repo's other strategies consistently use a hold cap to
  avoid indefinite drift).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _true_range(df: pd.DataFrame) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _vortex(df: pd.DataFrame, period: int):
    high, low, close = df["high"], df["low"], df["close"]
    vm_plus = (high - low.shift(1)).abs()
    vm_minus = (low - high.shift(1)).abs()
    tr = _true_range(df)

    vm_plus_sum = vm_plus.rolling(period).sum()
    vm_minus_sum = vm_minus.rolling(period).sum()
    tr_sum = tr.rolling(period).sum().replace(0, pd.NA)

    vi_plus = vm_plus_sum / tr_sum
    vi_minus = vm_minus_sum / tr_sum
    return vi_plus, vi_minus


def generate_signals(
    price_df: pd.DataFrame,
    vi_period: int = 14,
    atr_mult: float = 1.0,
    tp_sl_ratio: float = 1.5,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    vi_plus, vi_minus = _vortex(df, vi_period)
    tr = _true_range(df)
    atr = tr.rolling(vi_period).mean()

    vi_plus_above = vi_plus > vi_minus
    prev_above = vi_plus_above.shift(1).fillna(False)
    cross_up = vi_plus_above & (~prev_above)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_price = None
    sl_price = None
    tp_price = None

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            hi = high.iloc[i]
            lo = low.iloc[i]
            hit_sl = lo <= sl_price
            hit_tp = hi >= tp_price
            if hit_sl or hit_tp or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                entry_price = None
                continue
            position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]) and not pd.isna(atr.iloc[i]) and atr.iloc[i] > 0:
                in_position = True
                entry_idx = i
                entry_price = close.iloc[i]
                sl_price = entry_price - atr_mult * atr.iloc[i]
                tp_price = entry_price + tp_sl_ratio * atr_mult * atr.iloc[i]
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
