"""Strategy: 52-week-high proximity momentum, long-only, 200d SMA exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-03-015):
Source: Google AI-overview + search snippets for the 52-week-high momentum
effect (George & Hwang academic lineage) -- fetched via browser_exec after
web_search failed with a DDGS/TLS connection error for this query, and after
the primary quantifiedstrategies.com article itself was blocked by a bot-
verification challenge (same blocker hit in prior loop iterations
2026-09-03-004/-008). The behavioral story: investors anchor on a stock's
52-week high and underreact to continued strength once price approaches or
exceeds it, so buying near/at a rolling 252-trading-day high captures
positive momentum that persists longer than naive trailing-return signals
would suggest. Exit rule taken from the search snippet: hold until price
crosses below its 200-day SMA.

Distinct from every prior momentum strategy in this repo: this uses
proximity-to-rolling-high (a price *level*, like Donchian -008, but framed
as "within X% of the 252d high" rather than "new N-day high breakout") as
the entry trigger, combined with the same 200d SMA exit/trend-flip logic as
2026-09-03-004/-008/-012, rather than a trailing-return threshold (002/003/
004/012) or channel breakout (008).

Signal logic (long-only, per SAFETY.md)
------------
- Entry: close is within `pct_from_high` (e.g. 0.02 = 2%) of the rolling
  252-trading-day high (i.e. close >= high_252d * (1 - pct_from_high)).
- Exit: close < 200-day SMA (uptrend filter flips off).
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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
    pct_from_high: float = 0.02,
    trend_window: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rolling_high = close.rolling(lookback_days, min_periods=lookback_days).max()
    near_high = close >= (rolling_high * (1.0 - pct_from_high))

    trend_sma = close.rolling(trend_window, min_periods=trend_window).mean()
    below_trend = close < trend_sma

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(below_trend.iloc[i]):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(near_high.iloc[i]) and not bool(below_trend.fillna(True).iloc[i]):
                in_position = True
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
