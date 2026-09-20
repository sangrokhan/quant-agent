"""Strategy: 5/8/13/21 EMA Fibonacci-period ribbon stacking alignment.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-179):
Per multiple independent retail-trading sources (StockGro, Pocket Option,
gnlrw.com, and a nas100-trading SEO site, all describing the same
mechanical rule via Google search this iteration), the "5 8 13 21 EMA
Strategy" uses four EMAs at Fibonacci-adjacent periods (5, 8, 13, 21). A
bullish trend is confirmed when the EMAs are fully "stacked" in ascending
order of responsiveness: EMA(5) > EMA(8) > EMA(13) > EMA(21) (fastest above
slowest, in that exact order) -- i.e. full ribbon alignment, not just a
single crossover. None of these sources provide a rigorous numeric backtest
(informal retail/broker content, unlike quantifiedstrategies.com/Quantpedia
sources used elsewhere in this repo), so this is tested here from first
principles across this repo's standard grid.

This is distinct from the repo's existing (heavily saturated) GMMA/Rainbow-
MA family, which use 6-EMA clusters at periods 3/5/8/10/12/15 vs
30/35/40/45/50/60 (a much wider short-vs-long spread) or a recursive SMA
cascade -- here it's exactly 4 EMAs at close Fibonacci-adjacent periods
(5,8,13,21), all within a much tighter overall span, testing a materially
different responsiveness profile.

Signal logic
------------
- Four EMAs of close at periods p1 < p2 < p3 < p4 (default 5, 8, 13, 21).
- Long (position=1) whenever EMA(p1) > EMA(p2) > EMA(p3) > EMA(p4) (full
  bullish stack).
- Flat (position=0) whenever the stack order breaks in any way.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series
        {0,1} position series aligned to price_df.index.
    generate_returns(price_df, **params) -> pd.Series
        Position-weighted daily returns (position shifted by 1 day to avoid
        look-ahead bias), no transaction costs applied here.
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
    p1: int = 5,
    p2: int = 8,
    p3: int = 13,
    p4: int = 21,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ema1 = close.ewm(span=p1, adjust=False).mean()
    ema2 = close.ewm(span=p2, adjust=False).mean()
    ema3 = close.ewm(span=p3, adjust=False).mean()
    ema4 = close.ewm(span=p4, adjust=False).mean()

    stacked = (ema1 > ema2) & (ema2 > ema3) & (ema3 > ema4)
    position = stacked.fillna(False).astype(int)

    warmup = max(p1, p2, p3, p4)
    position.iloc[:warmup] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
