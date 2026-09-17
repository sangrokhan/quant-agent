"""Strategy: Dual Hull Moving Average (HMA) crossover trend-follow.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-057):
Per QuantifiedTrader's "Hull MA Crossover" backtest page
(https://quantifiedtrader.com/backtest/strategies/hull-ma-cross/): a FAST
Hull Moving Average crossing above a SLOW Hull Moving Average (source's
disclosed default parameters: fast HMA period 9, slow HMA period 18)
signals a momentum-confirmed trend shift, entering long faster than an
equivalent SMA/EMA crossover while remaining smoother than raw price
(source's own methodology text: "The HMA crossover fires faster than
SMA/EMA crossovers while remaining smooth"). Exit when slow HMA crosses
back above fast HMA. This is a genuinely distinct construction from the
repo's existing HMA entries: 2026-09-04-026/2026-09-09-013 (single HMA
line vs. raw CLOSE PRICE crossover) and 2026-09-06-097/128 (single HMA
SLOPE-turn, no second HMA line at all) -- this is the first two-HMA-line
crossover tested in this repo, directly per the source's own disclosed
strategy code (a `backtesting.py`-style `Strategy` class using
`crossover(hma_fast, hma_slow)`).

Signal logic
------------
- HMA(n) = WMA(2*WMA(close, n//2) - WMA(close, n), round(sqrt(n))) -- the
  standard Hull Moving Average formula (same construction as the repo's
  existing single-line HMA strategies).
- Entry (long): fast HMA(hma_fast) crosses from <= slow HMA(hma_slow) to >
  slow HMA (fresh bullish crossover).
- Exit: fast HMA crosses back from > slow HMA to <= slow HMA (fresh
  bearish crossover), OR a max_hold_days time-stop (this repo convention;
  source itself has no time-stop, only the crossover exit -- added here to
  avoid indefinite holds through prolonged consolidation).
- Flat otherwise; long-only, no shorting (per source, and per SAFETY.md no
  live order-placement).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _wma(series: pd.Series, window: int) -> pd.Series:
    weights = pd.Series(range(1, window + 1), dtype=float)
    return series.rolling(window).apply(
        lambda x: (x * weights.values).sum() / weights.sum(), raw=True
    )


def _hma(close: pd.Series, window: int) -> pd.Series:
    half_window = max(1, window // 2)
    sqrt_window = max(1, round(math.sqrt(window)))
    wma_half = _wma(close, half_window)
    wma_full = _wma(close, window)
    raw_hma = 2 * wma_half - wma_full
    return _wma(raw_hma, sqrt_window)


def generate_signals(
    price_df: pd.DataFrame,
    hma_fast: int = 9,
    hma_slow: int = 18,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fast = _hma(close, hma_fast)
    slow = _hma(close, hma_slow)

    fast_above = fast > slow
    entry = fast_above & (~fast_above.shift(1).fillna(False))
    exit_cross = (~fast_above) & (fast_above.shift(1).fillna(False))

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
