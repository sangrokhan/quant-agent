"""Strategy: Four Consecutive Down Days (unconditional short-term reversal).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-121):
Per QuantifiedStrategies.com's "Four Consecutive Down Days Trading
Strategy: A Guide"
(https://www.quantifiedstrategies.com/four-down-days-and-up/, accessed
2026-09-22 via browser_exec Google SERP + direct page load after
web_search DDGS backend returned only snippet results), the fully
disclosed rule (backtested by the source on SPY and several other ETFs
since 2005) is:

    - Entry: buy at the close after N (default 4) consecutive down-close
      days (each day's close < prior day's close).
    - Exit: sell at the close on the first day whose close is higher than
      the previous day's close (i.e. the first up-day ends the trade).
    - No trend filter, no stop-loss, no fixed hold period -- purely a
      "buy exhaustion after a losing streak, sell on first sign of
      reversal" mean-reversion rule.

This is distinct from this repo's existing multi-day-pullback entries:
- 2026-09-08-058 (Larry Connors "Multiple Days Up And Multiple Days
  Down"): requires 4-of-last-5 down days (not strictly consecutive) PLUS
  close<SMA(5) AND close>SMA(200) trend filters, exits on SMA(5) recross.
- 2026-09-10-033 (Quantpedia AI-assisted pullback): requires a 200-day-MA
  uptrend filter, vol-adjusted position sizing, and a FIXED holding period
  (not a signal-based exit).

This version has NO trend filter (source explicitly tests it unconditionally
across multiple asset types, including non-uptrending ones like GDX/FXI/EEM)
and uses a simple prior-close exit rather than an SMA recross or fixed hold.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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
    down_streak_days: int = 4,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    down_day = (close < close.shift(1)).astype(int)
    # Rolling sum of down_day over the last down_streak_days days == streak
    # length iff ALL of them were down days (sum == window size).
    streak_sum = down_day.rolling(down_streak_days).sum()
    entry = streak_sum >= down_streak_days
    entry = entry.fillna(False)

    up_day = close > close.shift(1)
    exit_signal = up_day.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
