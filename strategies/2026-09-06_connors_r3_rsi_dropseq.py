"""Strategy: Larry Connors' "R3" -- 3-day RSI(2) drop-sequence mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl for this run's id):
Per QuantifiedStrategies.com's writeup of Larry Connors' R3 strategy (Ch.4,
"High Probability ETF Trading", 2009)
(https://www.quantifiedstrategies.com/larry-connors-r3-strategy/), the
source's own trading rules are:
  1. Close must be above the 200-day moving average (favorable regime).
  2. The 2-day RSI drops three days in a row, and the FIRST of those three
     drops starts from a reading below 60 (i.e. RSI wasn't already
     overbought when the decline began).
  3. The 2-day RSI is today below 10.
  4. If 1-3 all true, enter LONG at today's close.
  5. Exit on today's close if the 2-day RSI is above 70.

This is a distinct entry condition from the plain RSI(2) oversold-threshold
strategy already tested in this repo (2026-09-03-005: RSI(2) <= a fixed
threshold, exit on SMA(5) cross) -- R3 requires a specific 3-day monotonic
RSI decline SEQUENCE starting from a non-overbought level, not just a single
day's RSI reading below a cutoff. The source's own rationale: a sequence of
weakening RSI readings (rather than one snapshot) filters out V-shaped single-
day dips and targets more persistent short-term selling pressure before the
extreme-oversold entry trigger.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
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


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 2,
    trend_window: int = 200,
    first_drop_below: float = 60.0,
    entry_below: float = 10.0,
    exit_above: float = 70.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rsi = _rsi(close, rsi_window)
    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    rsi_drop = rsi.diff() < 0  # today's RSI is lower than yesterday's
    # 3 consecutive drop-days: today, yesterday, day-before-yesterday all drops
    three_day_drop_seq = rsi_drop & rsi_drop.shift(1) & rsi_drop.shift(2)
    # "first day's drop is from a reading below 60" -> the RSI level TWO days
    # before today (i.e. the value the first drop started FROM) was below
    # first_drop_below.
    first_drop_start_level = rsi.shift(2)
    first_drop_ok = first_drop_start_level < first_drop_below

    entry = (
        uptrend.fillna(False)
        & three_day_drop_seq.fillna(False)
        & first_drop_ok.fillna(False)
        & (rsi < entry_below).fillna(False)
    )
    exit_signal = rsi > exit_above

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
