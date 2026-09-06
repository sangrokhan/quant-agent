"""Strategy: Gap-and-Go continuation (gap-up momentum), long-only, daily
bars.

Hypothesis (see knowledge_base id 2026-09-06-153):
Per TradeZella's "Gap and Go Strategy" guide
(https://www.tradezella.com/blog/gap-and-go-strategy): the strategy "trades
in the direction of a stock's opening gap, betting that the momentum that
caused the gap will continue... Gap size: minimum 2% from previous close...
Gaps larger than 10% can attract profit-taking early, which creates a fade
risk." First strategy in this repo trading WITH a gap's direction rather
than fading it (prior gap-related entries: 2026-09-03-010 gap-down-fade,
2026-09-04-095 fair-value-gap retracement -- both bet on gap reversal/
retracement, not continuation).

Adapted to this repo's daily-bar-only data (no intraday/pre-market data
available via data/loaders.py): rather than a same-day 30-90min intraday
entry, this operationalizes as entering at the CLOSE of the gap-up day
itself (the gap having already shown some continuation through the session
if the day closes green, consistent with the source's own filter excluding
gaps that get faded early) and holding for a short multi-day continuation
window, exiting on a stall/reversal or time-stop.

Signal logic
------------
- Gap-up day: today's open >= yesterday's close * (1 + min_gap_pct)
  (default 2%, per source), AND gap is not "too large" (<= max_gap_pct,
  default 10%, per source's own stated fade-risk cutoff for oversized gaps).
- Follow-through filter: today's close > today's open (the day closed green,
  i.e. gap held/extended rather than getting faded intraday -- our proxy
  for the source's "volume confirms real money is behind the move").
- Entry: long at today's close (shift(1) execution lag, same convention as
  every strategy in this repo).
- Exit: close falls back below the gap day's own open (failed follow-
  through), OR a max_hold_days time-stop (default 3, short continuation
  window per the strategy's own "first 30-90 minutes" spirit scaled to
  daily bars).

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def generate_signals(
    price_df: pd.DataFrame,
    min_gap_pct: float = 0.02,
    max_gap_pct: float = 0.10,
    max_hold_days: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    open_ = df["open"]
    close = df["close"]
    n = len(close)

    prev_close = close.shift(1)
    gap_pct = (open_ - prev_close) / prev_close

    gap_up = (gap_pct >= min_gap_pct) & (gap_pct <= max_gap_pct)
    follow_through = close > open_

    entry_signal = gap_up.fillna(False) & follow_through

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    gap_day_open = np.nan

    for i in range(n):
        if in_position:
            held = i - entry_idx
            failed = close.iloc[i] < gap_day_open
            if failed or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                gap_day_open = np.nan
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
                in_position = True
                entry_idx = i
                gap_day_open = open_.iloc[i]
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
