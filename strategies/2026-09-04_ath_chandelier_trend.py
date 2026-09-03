"""Strategy: All-time-high breakout entry with ATR chandelier trailing stop.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-025):
Per QuantPedia's "Trend-following Effect in Stocks" (source paper: Wilcox &
Crittenden, "Does Trend Following Work on Stocks?", 1983-2004 backtest,
indicative perf 19.3%/yr, MDD -33.74%, Sharpe 1.24): entering long when
price makes a new ALL-TIME HIGH close (not merely a 52-week/rolling-window
high) and exiting only via a ratcheting ATR(10) trailing stop ("chandelier
exit") captures the trend-following premium in stocks by cutting the left
tail of the return distribution (behavioral herding/under-reaction creates
persistent up-trends after a genuine breakout to new highs). This is the
first genuine chandelier/ATR-ratchet trailing-STOP-ONLY exit mechanism
tested in this repo, paired with an all-time-high (not rolling-window)
entry -- distinct from 52wk-high proximity momentum (2026-09-03-015, uses a
252-day rolling high + 200SMA cross exit) and SuperTrend (2026-09-03-014,
an ATR flip LINE used for both entry and exit).

Signal logic
------------
- ATR(atr_window) via the standard Wilder true-range average.
- All-time high tracked causally as the expanding max of daily closes up to
  (but not including) the current bar.
- Entry (long): today's close >= the all-time-high-so-far (a fresh
  breakout to a new all-time-high close).
- Chandelier trailing stop: once in a position, track the running highest
  close since entry; the stop level = running_high - atr_multiplier *
  ATR(atr_window) (ATR value frozen at entry, per the classic chandelier
  design, recomputed each bar from the running high). Exit when close
  drops below the current stop level.
- Flat otherwise; long-only, single position at a time (no pyramiding into
  new breakouts while already in a position -- matches the source's simple
  "hold until stopped out" rule).

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


def _atr(df: pd.DataFrame, atr_window: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(atr_window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    atr_window: int = 10,
    atr_multiplier: float = 3.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    atr = _atr(df, atr_window)

    # Causal all-time-high tracked strictly BEFORE today's bar (avoid
    # look-ahead: today's own close cannot confirm its own breakout target).
    all_time_high_prior = close.shift(1).expanding(min_periods=atr_window).max()
    entry = (close >= all_time_high_prior).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    running_high = None

    for i in range(len(close)):
        px = close.iloc[i]
        a = atr.iloc[i]
        if in_position:
            running_high = px if running_high is None else max(running_high, px)
            stop_level = running_high - atr_multiplier * (a if a == a else 0.0)
            if a == a and px < stop_level:
                in_position = False
                position.iloc[i] = 0
                running_high = None
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]) and a == a:
                in_position = True
                running_high = px
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
