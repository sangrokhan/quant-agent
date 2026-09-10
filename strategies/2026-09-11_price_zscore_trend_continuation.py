"""Strategy: Price Z-Score positive-threshold trend-continuation regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-039):
Per SetupAlpha's "I Tested 13 Momentum & Oscillator Regime Filters" (Part 2,
2026-06-21, visited this iteration -- https://setupalpha.substack.com/p/i-tested-13-momentum-and-oscillator-regime-filters):
1600+ backtests across SPY/QQQ/Bitcoin ranked 13 momentum/oscillator regime
filters. Rank #8 of 13 (near the paid tier) is:
    Regime: (C - Avg(C, zLen)) / StdDev(C, zLen) > zThresh / 10
i.e. long only while price's rolling z-score (distance from its own mean,
scaled by its own rolling std dev) is ABOVE a positive threshold -- price
trading unusually far above its recent average, used as a directional
trend-continuation regime switch. Source's own disclosed results: avoided
81% of 2008 and 77% of COVID, works on all 3 markets, ~2 points/year drag
(one of the better performers in that study), with the caveat that results
are sensitive to parameter choice.

This is DISTINCT from every z-score strategy already in this repo (e.g.
2026-09-04-082, 2026-09-04-083), all of which use a NEGATIVE z-score
threshold as a MEAN-REVERSION dip-buy signal (buy when price is unusually
far BELOW its average, expecting reversion up). This strategy instead uses
a POSITIVE z-score threshold as a TREND-CONTINUATION signal (stay long
while price is unusually far ABOVE its average, expecting the strength to
persist) -- the opposite construction and opposite trading philosophy on
the same underlying statistic.

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


def generate_signals(
    price_df: pd.DataFrame,
    z_window: int = 150,
    z_threshold: float = 0.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long whenever price's rolling z-score ((close - rolling mean) /
    rolling std) exceeds z_threshold; flat otherwise. No additional
    confirmation, per SetupAlpha's own disclosed rank-#8 rule.
    """
    df = _prep(price_df)
    close = df["close"]

    rolling_mean = close.rolling(z_window).mean()
    rolling_std = close.rolling(z_window).std()
    z_score = (close - rolling_mean) / rolling_std.replace(0.0, float("nan"))

    position = (z_score > z_threshold).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
