"""Strategy: Bullish Engulfing candlestick reversal, trend-filtered.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-102):
Per Google AI-overview synthesis (LuxAlgo/TradingView/apptrading.ai): a
Bullish Engulfing pattern -- a short-term decline (>= decline_days
consecutive down closes), followed by a bearish candle (Day 1), followed by
a bullish candle (Day 2) that opens at or below Day 1's close and closes
strictly above Day 1's open (fully engulfing Day 1's real body) -- signals
institutional buying pressure reversing a short-term downswing. Trading
this reversal within a long-term uptrend (close > 200d SMA, per source's
trend-filter guidance to "buy a pullback in a broader uptrend rather than
catching a falling knife") should give a tradeable long entry. Exit uses a
short mean-reversion-style hold (source's own risk-management suggests
exiting near the next resistance/DPO peak; this repo approximates with a
fixed max-hold + short SMA cross-back exit, consistent with this repo's
other short-hold mean-reversion strategies).

Signal logic
------------
- decline: close[t-1] < close[t-2] < ... for at least `decline_days`
  consecutive prior days (short-term downswing precondition).
- Day 1 (index i-1): bearish candle, close[i-1] < open[i-1].
- Day 2 (index i): bullish candle, close[i] > open[i], open[i] <=
  close[i-1] (opens at/below Day1's close), close[i] > open[i-1] (closes
  above Day1's open -- full real-body engulfment).
- Trend filter: close[i] > SMA(trend_window)[i] (200d uptrend, per source).
- Entry: all of the above true at bar i -> enter long at close[i].
- Exit: close crosses back above SMA(exit_window) (short-term mean-
  reversion target, default 5d) OR after max_hold_days OR trend filter
  breaks.
- Flat otherwise. Long-only per SAFETY.md.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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
    decline_days: int = 3,
    trend_window: int = 200,
    exit_window: int = 5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close, open_ = df["close"], df["open"]
    n = len(df)

    trend_sma = close.rolling(trend_window, min_periods=trend_window).mean()
    exit_sma = close.rolling(exit_window, min_periods=exit_window).mean()

    down_day = close < close.shift(1)
    decline_run = down_day.rolling(decline_days).sum() == decline_days

    day1_bearish = close.shift(1) < open_.shift(1)
    day2_bullish = close > open_
    engulf_open = open_ <= close.shift(1)
    engulf_close = close > open_.shift(1)

    entry = (
        decline_run.shift(1).fillna(False)
        & day1_bearish.fillna(False)
        & day2_bullish.fillna(False)
        & engulf_open.fillna(False)
        & engulf_close.fillna(False)
        & (close > trend_sma).fillna(False)
    )

    uptrend = (close > trend_sma).fillna(False)
    exit_meanrev = (close > exit_sma).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(n):
        if in_position:
            held = i - entry_idx
            exit_now = (held >= 1 and bool(exit_meanrev.iloc[i])) or (not bool(uptrend.iloc[i])) or held >= max_hold_days
            if exit_now:
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
