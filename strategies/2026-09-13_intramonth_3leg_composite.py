"""Strategy: Intramonth Momentum 3-Leg Composite (Nathan/Suominen/Tasa 2026,
extended by Quantpedia's "Sectoral Intramonth Momentum Cycle" blog post,
17 Aug 2026: https://quantpedia.com/sectoral-intramonth-momentum-cycle-exploiting-turn-of-the-month-patterns-in-sector-etf-strategies/).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
The source documents THREE distinct legs within a calendar month, each with
opposite-sign momentum behavior:
  1. Day 1 of the month: trailing 252-day momentum CONTINUES (momentum
     positive -> next-day-1 return positive).
  2. Days 2-3 of the month: the SAME momentum signal REVERSES (momentum
     positive -> next 2-3 days tend to give back the day-1 gain). Source's
     own long-short sector portfolio profits from this reversal; the
     long-only single-instrument adaptation here simply goes FLAT during
     this window rather than shorting.
  3. 10-to-5 trading days before month-end: a SEPARATE, independent
     momentum leg re-emerges (per source: "a third, independent leg of the
     cycle emerges in the window from ten to five trading days before
     month-end").

This is mechanically distinct from this repo's prior single-window
intramonth-momentum test (id 2026-09-08-142, rejected decisively) which
only implemented ONE calendar window (a single N-day block gated by
absolute momentum) with a single end_offset parameter. This strategy
stitches THREE separate legs of the same underlying calendar cycle, each
independently gated by its own trailing-momentum sign, and treats the
known-reversal Leg 2 as an explicit FLAT period rather than ignoring it
(the prior version's single window straddled through where Leg 2 would
sit, diluting the signal with a period the source itself says works in
the OPPOSITE direction).

Signal logic
------------
- lookback_days: trailing absolute-momentum lookback (source: 252 trading
  days, ~12 months).
- Each trading day is classified by its position within the current
  calendar month (0-indexed trading-day-of-month count from the front,
  and trading-days-remaining-until-month-end count from the back).
- Leg 1 window: trading-day-of-month in [0, leg1_days) -- long if trailing
  lookback_days momentum > 0, else flat.
- Leg 2 window: trading-day-of-month in [leg1_days, leg1_days+leg2_days)
  -- always flat (this is the source's documented reversal window; a
  long-only strategy cannot profit from shorting it, so it is skipped).
- Leg 3 window: trading-days-remaining-until-month-end in
  [leg3_end_offset, leg3_end_offset+leg3_days) -- long if trailing
  lookback_days momentum > 0, else flat (same momentum sign test as Leg 1,
  applied independently in this separate calendar window).
- Flat everywhere else (the bulk of the month, matching the source's own
  low-time-invested framing: "invested fewer than half the trading days
  each month").

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index.
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
    leg1_days: int = 1,
    leg2_days: int = 2,
    leg3_days: int = 6,
    leg3_end_offset: int = 4,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    idx = close.index

    # Trailing absolute momentum sign (source's convention: full trailing
    # lookback_days return, no skip-month).
    momentum = close.pct_change(lookback_days)
    momentum_positive = (momentum > 0).fillna(False)

    # Trading-day-of-month count (0-indexed) and trading-days-remaining
    # until month-end, computed causally from the DatetimeIndex.
    month_key = pd.Series(idx.year * 100 + idx.month, index=idx)
    day_of_month_count = month_key.groupby(month_key).cumcount()
    # trading days remaining in the month (0 = last trading day of month)
    days_in_month_total = month_key.groupby(month_key).transform("size")
    days_remaining = (days_in_month_total - 1) - day_of_month_count

    leg1_mask = day_of_month_count < leg1_days
    leg3_mask = (days_remaining >= leg3_end_offset) & (
        days_remaining < (leg3_end_offset + leg3_days)
    )
    # Leg 2 window is explicitly excluded from any long position (flat).

    long_mask = (leg1_mask | leg3_mask) & momentum_positive

    position = long_mask.astype(int)
    position.index = idx
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
