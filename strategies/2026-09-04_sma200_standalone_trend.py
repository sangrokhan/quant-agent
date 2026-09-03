"""Strategy: Standalone 200-day SMA trend-following (price-position rule).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-074):
Per BoringEdge's Bitcoin Golden Cross backtest article: the source's own
comparison found the SIMPLER standalone 200-day SMA price-position rule
(long when close is above SMA(200), flat when below -- no second moving
average required) BEAT the classic 50/200 golden-cross two-MA crossover on
their own BTC data (26.1% CAGR / -64.1% MDD vs the golden-cross's 20.0%
CAGR / -66.8% MDD), attributing the golden cross's underperformance to "the
extra lag from waiting for two moving averages to cross". This repo has
tested SMA(200) extensively as a GATING FILTER alongside another signal
(OBV, SD-channel, CMO, TEMA, etc.) but never as a standalone single-
indicator strategy on its own. Testing the bare single-SMA(200)
price-position rule directly, long-only, no second signal required.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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
    sma_window: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long whenever close is above its own rolling SMA(sma_window); flat
    otherwise. No second moving average, no crossover mechanics -- a pure
    price-vs-single-MA position rule.
    """
    df = _prep(price_df)
    close = df["close"]
    sma = close.rolling(sma_window).mean()

    position = (close > sma).astype(int)
    position[sma.isna()] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
