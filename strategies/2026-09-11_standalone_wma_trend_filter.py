"""Strategy: Standalone WMA trend-following regime filter (long/flat).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-038):
Per SetupAlpha's "I Tested 20 Trend-Based Regime Filters" (2026-06-14,
visited this iteration -- https://setupalpha.substack.com/p/i-tested-20-trend-based-regime-filters):
2700+ backtests across SPY/QQQ/Bitcoin ranking 20 trend-based regime
filters worst-to-best. The disclosed rule for rank #11 (solid performer,
works across all 3 markets, ~2 points/yr drag, avoided 84% of the 2008
crash) is the simplest possible construction: `Regime: C > WMA(C, maLen)`
-- price above its own Weighted Moving Average, no additional
confirmation/band/adaptivity. Notably the source's OWN comparative
finding is that this plain construction outperforms (has less whipsaw
cost than) the more elaborate adaptive/banded variants ranked above it in
their worse tier (TEMA #20, HMA #17, KAMA #13, SMA+/-band #12) -- so this
is worth testing standalone precisely because the source's own multi-year,
multi-market study found it beats those more "sophisticated" alternatives.

This repo has WMA only embedded as a component/filter inside other
strategies (e.g. Kaufman ER+WMA gate 2026-09-04-120), never tested as a
standalone long/flat trend-following strategy in its own right -- this
fills that gap.

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


def _wma(close: pd.Series, window: int) -> pd.Series:
    weights = pd.Series(range(1, window + 1), dtype=float)

    def _weighted(x):
        return (x * weights.values).sum() / weights.sum()

    return close.rolling(window).apply(_weighted, raw=True)


def generate_signals(
    price_df: pd.DataFrame,
    wma_window: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long whenever close > its own WMA(wma_window); flat otherwise. No
    additional confirmation, band, or time-stop -- the plain rule per
    SetupAlpha's own rank #11 disclosure.
    """
    df = _prep(price_df)
    close = df["close"]
    wma = _wma(close, wma_window)
    position = (close > wma).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
