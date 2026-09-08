"""Strategy: 12-1 Month Momentum (Jegadeesh-Titman skip-month convention).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-032):
Per quant-investing.com's "12-1 month momentum" screener explainer (read
this cron trigger): Price Index 12m Minus 1m = price(t - 1 month) /
price(t - 12 months) -- i.e. trailing 12-month return EXCLUDING the most
recent month, because "studies have shown [a large jump in share price over
the past month] usually reverses shortly thereafter" (the well-documented
short-term reversal effect). This is distinct from this repo's
already-rejected plain 12-month time-series momentum (2026-09-03-012, which
explicitly used NO skip-month, citing an index-level academic convention
that skip-month is a "stock-level-only" adjustment) -- this iteration tests
whether adding the skip-month exclusion changes the outcome on QQQ/SPY/
BTC/ETH, i.e. whether the short-term-reversal contamination the skip-month
convention is designed to filter out was actually hurting the un-skipped
version's signal quality.

Signal logic
------------
- Momentum ratio = close(t - skip_days) / close(t - lookback_days)
  (skip_days ~= 21 trading days = 1 month; lookback_days ~= 252 trading
  days = 12 months, per the source's own month-based framing translated to
  daily trading-day counts).
- Long entry (long-only, time-series absolute-momentum interpretation
  since this repo has single-asset data, not a cross-sectional universe):
  momentum ratio > entry_threshold (1.0 = flat vs 12 months ago,
  excluding the last month's contribution).
- Exit: momentum ratio drops to/below exit_threshold, or a max_hold_days
  safety time-stop is not used here since this is a persistent
  trend-following regime state (monthly-effective rebalance via the daily
  ratio check), matching the source's own monthly-rebalance screener
  design and this repo's existing TSMOM strategy's convention
  (2026-09-03-012).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    lookback_days: int = 252,
    skip_days: int = 21,
    entry_threshold: float = 1.0,
    exit_threshold: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    price_skip_ago = close.shift(skip_days)
    price_lookback_ago = close.shift(lookback_days)
    momentum_ratio = price_skip_ago / price_lookback_ago

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False

    n = len(close)
    for i in range(n):
        r = momentum_ratio.iloc[i]
        if pd.isna(r):
            continue
        if in_position:
            if r <= exit_threshold:
                in_position = False
            else:
                position.iloc[i] = 1
        else:
            if r > entry_threshold:
                in_position = True
                position.iloc[i] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
