"""Strategy: Larry Connors' Multiple Days Down (MDD) mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-058):
Per quantifiedstrategies.com's disclosure of Larry Connors' "Multiple Days
Up And Multiple Days Down" strategy (High Probability Trading, Ch.6): ETFs
tend to revert to the mean after a short burst of consecutive down days,
provided the longer-term trend is still intact. The source's own summarized
rule set:
  1. Close > SMA(200) (long-term uptrend intact).
  2. Close < SMA(5) (short-term weakness).
  3. The ETF has closed down on at least `down_days_required` of the last
     `lookback_days` trading days (default 4 of 5).
  4. If 1-3 all true, enter long at the close.
  5. Exit (sell) at the close on the first day the close is back above its
     own SMA(5). No stop-loss (source's own explicit design choice).

First "multiple-days-down streak" mean-reversion construction in this repo
(distinct from the already-tested Connors RSI(2)/QS-RSI/StochRSI/CRSI family,
which use a smoothed oscillator threshold rather than a raw consecutive-
down-day count as the oversold trigger). Source:
https://www.quantifiedstrategies.com/multiple-days-up-and-multiple-days-down/

Signal logic
------------
- long_trend = close > SMA(200)
- short_weak = close < SMA(5)
- down_day = close < close.shift(1)
- streak_down_count = rolling count of down_day over the trailing
  lookback_days window
- entry = long_trend & short_weak & (streak_down_count >= down_days_required)
- exit = close crosses back above SMA(5) (source's stated exit trigger)
- No stop-loss, no max-hold-days -- matches source's explicit design
  (only the SMA(5) recovery closes the trade).

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
    trend_window: int = 200,
    short_ma_window: int = 5,
    lookback_days: int = 5,
    down_days_required: int = 4,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma_trend = close.rolling(trend_window).mean()
    sma_short = close.rolling(short_ma_window).mean()

    down_day = (close < close.shift(1)).astype(int)
    streak_down_count = down_day.rolling(lookback_days).sum()

    long_trend = close > sma_trend
    short_weak = close < sma_short
    entry_condition = long_trend & short_weak & (streak_down_count >= down_days_required)
    exit_condition = close > sma_short

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_condition.iloc[i]):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_condition.iloc[i]):
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
