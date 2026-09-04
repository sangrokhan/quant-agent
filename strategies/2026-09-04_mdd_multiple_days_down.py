"""Strategy: Larry Connors' Multiple Days Down (MDD) mean-reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-099):
Per Larry Connors' "High Probability Trading" (Chapter 6): buy an ETF when
it has fallen on at least `down_days_required` of the last `window` trading
days (default 4 of 5), while in a long-term uptrend (close > 200-day SMA)
and currently trading below its short-term mean (close < 5-day SMA). Exit
when price closes back above the 5-day SMA. No stop-loss (per the source's
own rule). This is distinct from every prior "consecutive N days" strategy
in this repo (TD Sequential's strict 9-consecutive-bar count, Heikin-Ashi/
Renko's consecutive-same-color-bar trend-following) since it uses a more
forgiving "N of the last M days" down-day count (mean reversion, not
trend-following) rather than requiring an unbroken streak.

Signal logic
------------
- down_day[t] = close[t] < close[t-1]
- down_count[t] = sum(down_day) over the trailing `window` days (default 5)
- Entry: close[t] > SMA(trend_window)[t] (200d uptrend) AND
  close[t] < SMA(short_window)[t] (5d, below short-term mean) AND
  down_count[t] >= down_days_required (default 4)
- Exit: close[t] > SMA(short_window)[t] (reverted back above the 5d SMA)
- No stop-loss, no max-hold override (per source's explicit "no stop-loss"
  rule) -- position simply held until the mean-reversion exit condition
  fires, however long that takes.
- Flat (no position) otherwise. Long-only per SAFETY.md.

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
    trend_window: int = 200,
    short_window: int = 5,
    down_window: int = 5,
    down_days_required: int = 4,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    trend_sma = close.rolling(trend_window, min_periods=trend_window).mean()
    short_sma = close.rolling(short_window, min_periods=short_window).mean()

    down_day = (close < close.shift(1)).astype(int)
    down_count = down_day.rolling(down_window, min_periods=down_window).sum()

    entry = (
        (close > trend_sma).fillna(False)
        & (close < short_sma).fillna(False)
        & (down_count >= down_days_required).fillna(False)
    )
    exit_signal = (close > short_sma).fillna(False)

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
