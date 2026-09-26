"""Strategy: Larry Williams' "Outside Day" reversal + TDW (Trading-Day-of-Week) filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD), sourced from
tradingcoachu.com's summary of Larry Williams' "Long-Term Secrets to
Short-Term Trading" (read via browser_exec after web_search's DDGS backend
returned results only for tangential pages -- confirmed via direct browse).
Williams' own disclosed rule (his S&P500 1982-1998 backtest reportedly
achieved 86% winning trades, 39 consecutive wins, profit factor 3.02 when
combined with a "buy on any day but Thursday" TDW filter):

  1. An "outside day" forms: today's high > yesterday's high AND today's
     low < yesterday's low (today's range fully engulfs yesterday's).
  2. Today's CLOSE is below YESTERDAY's low (a decisively bearish outside
     day -- not just an outside day, one that closes weak).
  3. The NEXT day opens even LOWER than today's (bearish) close --
     confirming continued panic/exhaustion selling.
  4. Buy at that next day's open (a contrarian bear-trap reversal bet: the
     gap-down-after-already-closing-weak is read as capitulation/exhaustion
     rather than continuation).
  5. Exit at the first subsequent day whose close is profitable relative to
     the entry (Williams doesn't give an exact exit rule per the source;
     approximated here as first close > entry_price, or a max_hold_days
     safety time-stop if no such close occurs).
  6. TDW filter: entries are skipped on a configurable day-of-week
     (Williams' own found best exclusion was Thursday, but this is
     source-corroborated OPTIMIZED-post-hoc via Seasonax-style search, so
     exposed as a tunable parameter here rather than hardcoded).

Distinct from all prior outside-day entries in this repo: 2026-09-08-086
(Bulkowski continuation direction, no TDW filter, no next-day-gap
confirmation), 2026-09-08-122 (reversal but triggered by close-position/
volume, not the specific "close below prior low + next-day gap-down open"
sequence), 2026-09-12-191/193 (Kaufman Key Reversal / Wide Ranging Days,
different trigger conditions entirely). This is the first strategy in this
repo combining a specific bearish-outside-day + confirming-gap-down
CONTRARIAN reversal trigger with an explicit day-of-week exclusion filter.

Interface contract for validators (see validation/validators.py) and grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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
    exclude_weekday: int = 3,  # 0=Mon,...,3=Thu,...,6=Sun (Williams: skip Thursday)
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry trigger (evaluated at day t's open, i.e. signal set the day
    before at day t-1's close):
        day (t-1) is a bearish outside day: high[t-1]>high[t-2] AND
        low[t-1]<low[t-2] AND close[t-1]<low[t-2];
        AND open[t] < close[t-1] (confirming gap-down continuation);
        AND weekday of day t != exclude_weekday.
    Position goes long from day t through the first subsequent day whose
    close exceeds the entry price (day t's open), or max_hold_days trading
    days, whichever comes first.
    """
    df = _prep(price_df)
    idx = df.index
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    open_ = df["open"] if "open" in df.columns else df["close"]
    close = df["close"]

    bearish_outside = (high > high.shift(1)) & (low < low.shift(1)) & (
        close < low.shift(1)
    )

    pos = pd.Series(0, index=idx, dtype=int)
    n = len(idx)

    for i in range(2, n):
        # Check if day i-1 was a bearish outside day, and day i gaps down
        # further, and day i isn't the excluded weekday.
        if not bool(bearish_outside.iloc[i - 1]):
            continue
        if not (open_.iloc[i] < close.iloc[i - 1]):
            continue
        if idx[i].weekday() == exclude_weekday:
            continue
        # Avoid re-entering while already in an active position.
        if pos.iloc[i] == 1:
            continue

        entry_price = open_.iloc[i]
        hold_end = min(i + max_hold_days, n - 1)
        exit_i = hold_end
        for j in range(i, hold_end + 1):
            if close.iloc[j] > entry_price:
                exit_i = j
                break
        pos.iloc[i : exit_i + 1] = 1

    return pos


def generate_returns(
    price_df: pd.DataFrame,
    exclude_weekday: int = 3,
    max_hold_days: int = 10,
) -> pd.Series:
    """Daily strategy returns, position lagged by 1 day to avoid look-ahead."""
    df = _prep(price_df)
    pos = generate_signals(df, exclude_weekday=exclude_weekday, max_hold_days=max_hold_days)
    price_col = "close" if "close" in df.columns else df.columns[0]
    daily_ret = df[price_col].pct_change()
    strat_ret = pos.shift(1).fillna(0) * daily_ret
    return strat_ret.fillna(0.0)
