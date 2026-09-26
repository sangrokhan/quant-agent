"""Strategy: Weekly Inside-Week / Mother-Week breakout (higher-timeframe resample).

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD), sourced from a
Google AI-overview synthesis (PriceAction.com/TradingView/FTMO explainers,
read via browser_exec after web_search's DDGS backend returned zero results
for the query). The Weekly Inside-Week pattern: a "Mother Week" (any weekly
candle) is followed by an "Inside Week" whose high/low are fully contained
within the Mother Week's high/low (volatility contraction / indecision at
the weekly timeframe). The disclosed rule: place breakout entries at the
Mother Week's high (long) / low (short); the stop sits on the opposite
side of the Mother Week's range; target 2-3x the Mother Week range.

This repo's daily-timeframe Inside-Bar/Mother-Bar breakout family is
heavily saturated (28+ prior entries, e.g. 2026-09-04-090, all rejected).
This strategy is a genuinely distinct HIGHER-TIMEFRAME construction: price
data is resampled to WEEKLY OHLC bars first (via pandas .resample("W")),
the inside-week/mother-week pattern is detected on that weekly series, and
only then is the breakout level (mother week's high, long-only per
SAFETY.md) checked against subsequent DAILY closes for the actual entry
trigger -- this genuinely differs from all daily-bar-only inside-bar
strategies already in this repo, and is a distinct novel angle from the
recently-tested weekly-resampled Stochastic bucket gate (2026-09-22-051,
rejected), which used a different oscillator-based (not range-breakout)
weekly signal.

Long-only adaptation: enter long when a daily close breaks above the
active mother-week's high (following a confirmed inside week), exit when
price hits a stop (mother-week's low) or a profit target
(target_mult * mother_week_range above breakout), or after max_hold_days
if neither is hit.

Interface contract for validators (see validation/validators.py) and grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _weekly_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """Resample daily OHLC to weekly bars (week ending Friday/last trading day)."""
    o = df["open"] if "open" in df.columns else df["close"]
    h = df["high"] if "high" in df.columns else df["close"]
    l = df["low"] if "low" in df.columns else df["close"]
    c = df["close"]
    weekly = pd.DataFrame(
        {
            "open": o.resample("W").first(),
            "high": h.resample("W").max(),
            "low": l.resample("W").min(),
            "close": c.resample("W").last(),
        }
    ).dropna()
    return weekly


def generate_signals(
    price_df: pd.DataFrame,
    target_mult: float = 2.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Detects weekly inside-week patterns (a weekly bar fully contained in
    the prior weekly bar's high/low range). While an inside-week's mother
    week is "active" (i.e. after the inside week completes, until the next
    breakout/stop/target/time-stop resolution), goes long on the first
    daily close that breaks above the mother week's high, holding until:
    - daily close drops back below the mother week's low (stop), or
    - daily close reaches mother_week_high + target_mult*mother_week_range
      (target), or
    - max_hold_days trading days have elapsed since entry (time-stop).
    """
    df = _prep(price_df)
    idx = df.index
    close = df["close"]

    weekly = _weekly_ohlc(df)
    w_high = weekly["high"]
    w_low = weekly["low"]

    is_inside = (w_high <= w_high.shift(1)) & (w_low >= w_low.shift(1))
    # The "mother week" for an inside week at position i is week i-1.
    mother_high = w_high.shift(1)
    mother_low = w_low.shift(1)

    # Build a per-daily-bar "active mother week range" series: for each
    # calendar week that is itself an inside week, propagate its mother
    # week's high/low forward to daily bars in the FOLLOWING week (the
    # breakout attempt window), decaying after max_hold_days.
    pos = pd.Series(0, index=idx, dtype=int)

    inside_week_ends = weekly.index[is_inside.fillna(False)]
    for we in inside_week_ends:
        m_high = mother_high.loc[we]
        m_low = mother_low.loc[we]
        if pd.isna(m_high) or pd.isna(m_low):
            continue
        mother_range = m_high - m_low
        if mother_range <= 0:
            continue

        # Breakout attempt window: daily bars strictly after the inside
        # week's end date.
        window_mask = idx > we
        window_idx = idx[window_mask]
        if len(window_idx) == 0:
            continue

        entry_date = None
        for d in window_idx:
            if close.loc[d] > m_high:
                entry_date = d
                break
            # If price breaks the mother week's low before breaking out
            # upward, the setup is invalidated (long-only scope).
            if close.loc[d] < m_low:
                break

        if entry_date is None:
            continue

        target_price = m_high + target_mult * mother_range
        entry_loc = idx.get_loc(entry_date)
        hold_end_loc = min(entry_loc + max_hold_days, len(idx) - 1)

        exit_loc = hold_end_loc
        for j in range(entry_loc, hold_end_loc + 1):
            px = close.iloc[j]
            if px < m_low or px >= target_price:
                exit_loc = j
                break

        pos.iloc[entry_loc : exit_loc + 1] = 1

    return pos


def generate_returns(
    price_df: pd.DataFrame,
    target_mult: float = 2.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Daily strategy returns, position lagged by 1 day to avoid look-ahead."""
    df = _prep(price_df)
    pos = generate_signals(df, target_mult=target_mult, max_hold_days=max_hold_days)
    price_col = "close" if "close" in df.columns else df.columns[0]
    daily_ret = df[price_col].pct_change()
    strat_ret = pos.shift(1).fillna(0) * daily_ret
    return strat_ret.fillna(0.0)
