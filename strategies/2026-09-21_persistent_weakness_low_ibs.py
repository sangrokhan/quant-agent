"""Strategy: Persistent Weakness (N-day down-streak) + Low IBS dual-oversold
mean reversion, gated by a long-term uptrend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-174):
Per QuantifiedStrategies.com's "ES Persistent Weakness + Low IBS" course
lesson title (members-only content, exact numeric thresholds paywalled;
concept name freely visible), a stretch of `streak_days` CONSECUTIVE
down-closes ("persistent weakness") combined with a simultaneously LOW
Internal Bar Strength reading (IBS = (close-low)/(high-low), close near
the day's own low) signals a deeper, more reliable oversold condition than
either signal alone -- persistent weakness captures the multi-day
DURATION of the decline while IBS captures the INTRADAY conviction of the
latest down day (closing weak within its own range, not just closing
lower than yesterday). This repo has 13+ prior IBS-family entries (plain
threshold, RSI+IBS dual-oversold in 2026-09-20-082, SMA+IBS gates) but
none combine IBS with a consecutive-down-day STREAK length specifically
-- this is a genuinely distinct dual-oversold construction (duration-based
weakness gate, not an oscillator-based one like RSI).

Signal logic
------------
- Persistent weakness: the last `streak_days` daily closes are each lower
  than the prior day's close (a clean N-day down-streak).
- Low IBS: today's IBS = (close-low)/(high-low) is below `ibs_threshold`
  (close near today's own low, weak intraday conviction).
- Trend filter: close > SMA(trend_window) (only buy dips within an
  established uptrend, not falling knives in a downtrend).
- Entry: long at today's close when all three conditions hold
  simultaneously.
- Exit: IBS recovers above `ibs_exit_threshold` (close moves back toward
  the top of its own range, a signal-based mean-reversion exit) OR
  max_hold_days reached, whichever first.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position series)
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
    streak_days: int = 3,
    ibs_threshold: float = 0.3,
    ibs_exit_threshold: float = 0.7,
    trend_window: int = 200,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    idx = df.index
    n = len(idx)

    close = df["close"]
    high = df["high"]
    low = df["low"]

    down_day = close < close.shift(1)
    down_streak = down_day.rolling(streak_days).sum() == streak_days

    range_ = (high - low).replace(0, pd.NA)
    ibs = (close - low) / range_

    trend_sma = close.rolling(trend_window).mean()
    trend_ok = close > trend_sma

    entry_signal = down_streak.fillna(False) & (ibs <= ibs_threshold).fillna(False) & trend_ok.fillna(False)

    position = pd.Series(0, index=idx, dtype=int)
    in_position = False
    entry_i = -1
    for i in range(n):
        if in_position:
            hold_days = i - entry_i
            exit_signal = (pd.notna(ibs.iloc[i]) and ibs.iloc[i] >= ibs_exit_threshold) or hold_days >= max_hold_days
            if exit_signal:
                in_position = False
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
                in_position = True
                entry_i = i
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    streak_days: int = 3,
    ibs_threshold: float = 0.3,
    ibs_exit_threshold: float = 0.7,
    trend_window: int = 200,
    max_hold_days: int = 10,
) -> pd.Series:
    """Daily strategy returns (no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        streak_days=streak_days,
        ibs_threshold=ibs_threshold,
        ibs_exit_threshold=ibs_exit_threshold,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
