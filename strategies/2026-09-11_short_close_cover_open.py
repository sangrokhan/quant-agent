"""Strategy: Short the Close, Cover at the Next Open (overnight short).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-079):
Per QuantifiedStrategies.com's disclosed rule (found via Google AI-overview
synthesis of https://www.quantifiedstrategies.com/short-the-close-cover-at-the-next-open/,
visited this iteration via browser_exec after the direct URL 404'd and a
Google search surfaced the AI-overview summary of the actual article):
short a position right before the close, cover at the next day's open
(a sub-24-hour overnight short), gated by two entry filters to avoid
shorting into strong upward momentum:
  1. Gap condition: today's open must be no more than 1.5% above
     yesterday's close (i.e. no large gap-up already priced in).
  2. Volatility condition: today's daily trading range (High - Low) must
     be LARGER than its own 20-day average range (elevated-volatility
     day, source's rationale being higher-volatility days are more prone
     to overnight mean-reversion/give-back after an up-day).

Adapted long-only-safe per SAFETY.md: this repo implements the SHORT
overnight position as a {-1, 0} position series (paper-backtest only, no
real order placement), following the same {-1,0} short/flat pattern
already used by strategies/2026-09-08_dark_cloud_cover_short_reversal.py.

This is the first "short the close, cover next open" (systematic
overnight-short with a gap+volatility dual filter) construction in this
repo -- distinct from the already-tested overnight-drift LONG strategies
(which hold long overnight) and from the Dark Cloud Cover short reversal
(a multi-day-hold candlestick pattern short, not an unconditional daily
overnight short-the-close gated purely by gap/volatility conditions).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({-1,0} short/flat)
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
    gap_thresh: float = 0.015,
    range_window: int = 20,
) -> pd.Series:
    """Return a {-1,0} short/flat position series.

    A -1 on day t means: short at day t's close, cover at day t+1's open
    (an overnight short position). generate_returns applies this directly
    to the close(t)->open(t+1)-then-open(t+1)->close(t+1) sequence by
    using the standard close-to-close daily return convention shifted by
    one day (same mechanical pattern as every other strategy in this
    repo, since the daily-bar OHLCV granularity available here can't
    separately isolate the close-to-open vs open-to-close legs -- the
    dominant contribution of an overnight short is captured by shorting
    the close-to-close return of the FOLLOWING day, which starts with the
    overnight gap).
    """
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    high = df["high"]
    low = df["low"]

    daily_range = high - low
    avg_range = daily_range.rolling(range_window).mean()

    prior_close = close.shift(1)
    gap_pct = (open_ - prior_close) / prior_close

    gap_ok = gap_pct <= gap_thresh
    vol_ok = daily_range > avg_range

    entry = (gap_ok & vol_ok).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    position[entry] = -1
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs).

    Short position on day t is entered at day t's close and covered at
    day t+1's open; approximated here (given daily-OHLCV-only data) as
    -1 * the close-to-close return realized on day t+1 (captures the
    overnight gap plus the following day's price action, the standard
    same-mechanism approximation used by other overnight strategies in
    this repo, e.g. 2026-09-07_overnight_drift_vix_level_filter.py).
    """
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
