"""Strategy: SuperTrend(ATR-based) long-only trend follower.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-005):
Per CoinQuant's ETHUSDT backtest
(https://www.coinquant.ai/blog/supertrend-on-ethereum-6-years-of-backtest-results),
the SuperTrend indicator (ATR-based dynamic trailing support/resistance
line) flipping bullish (close crosses above the SuperTrend line) marks a
sustained trending move worth riding long, and flipping bearish (close
crosses below) marks the exit. Source's own ETH/4H numbers (period=10,
mult=3.0): +810.8% return, Sharpe 0.90 (just below the "strong" 1.0 bar),
win rate 34.4%, MDD 53.14%, profit factor 1.20 -- explicitly a moderate,
high-drawdown result. First SuperTrend strategy in this repo; testing here
on DAILY bars across QQQ/SPY/BTC/ETH (source used 4H ETH-only) to see if it
clears this repo's Sharpe>=1.0 / MDD<=25% bars, or if the source's own
sub-1.0 Sharpe / >50% MDD flags carry over.

Signal logic
------------
- SuperTrend(atr_window, mult): ATR-based band around (high+low)/2 basis.
  Upper band = basis + mult*ATR, lower band = basis - mult*ATR. The active
  SuperTrend line switches between upper/lower band depending on trend
  direction, ratcheting to never move against the current trend (standard
  SuperTrend construction).
- Entry (long): close crosses above the SuperTrend line (bullish flip).
- Exit: close crosses below the SuperTrend line (bearish flip).
- Long-only, always in market when trend is bullish (no separate max-hold;
  the trend-following nature means holds can be long by design, matching
  the source's own no-filter rule set).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def _supertrend(df: pd.DataFrame, atr_window: int, mult: float) -> pd.Series:
    """Return the SuperTrend line value at each bar."""
    high, low, close = df["high"], df["low"], df["close"]
    hl2 = (high + low) / 2.0
    atr = _atr(df, atr_window)

    basic_upper = hl2 + mult * atr
    basic_lower = hl2 - mult * atr

    n = len(df)
    final_upper = np.full(n, np.nan)
    final_lower = np.full(n, np.nan)
    supertrend = np.full(n, np.nan)
    direction = np.ones(n, dtype=int)  # 1 = bullish (below price), -1 = bearish

    bu = basic_upper.values
    bl = basic_lower.values
    c = close.values

    for i in range(n):
        if np.isnan(bu[i]) or np.isnan(bl[i]):
            continue
        if i == 0 or np.isnan(final_upper[i - 1]):
            final_upper[i] = bu[i]
            final_lower[i] = bl[i]
            direction[i] = 1 if c[i] >= final_lower[i] else -1
            supertrend[i] = final_lower[i] if direction[i] == 1 else final_upper[i]
            continue

        final_upper[i] = bu[i] if (bu[i] < final_upper[i - 1] or c[i - 1] > final_upper[i - 1]) else final_upper[i - 1]
        final_lower[i] = bl[i] if (bl[i] > final_lower[i - 1] or c[i - 1] < final_lower[i - 1]) else final_lower[i - 1]

        prev_dir = direction[i - 1]
        if prev_dir == 1:
            direction[i] = -1 if c[i] < final_lower[i] else 1
        else:
            direction[i] = 1 if c[i] > final_upper[i] else -1

        supertrend[i] = final_lower[i] if direction[i] == 1 else final_upper[i]

    return pd.Series(supertrend, index=df.index)


def generate_signals(
    price_df: pd.DataFrame,
    atr_window: int = 10,
    mult: float = 3.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    st_line = _supertrend(df, atr_window, mult)

    position = (close > st_line).astype(int)
    position = position.where(st_line.notna(), 0)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
