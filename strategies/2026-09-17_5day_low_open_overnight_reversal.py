"""Strategy: 5-Day-Low-Open + Bullish-Close overnight mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-007):
Per QuantifiedStrategies.com's "5-Day Low Overnight Trading Strategy"
(https://www.quantifiedstrategies.com/5-day-low-overnight-trading-strategy/,
read this iteration via browser_exec; Google search results were used to
find it after `web_search` failed with a backend RequestError):

  "trading the S&P 500 when it opens at a 5-day low but closes higher than
   its opening price. Enter at the close, exit at the next day's open."

Disclosed backtest (2005+): 175 trades, avg gain/trade 0.31%, win rate 62%,
MDD 13%. The exact numeric trading rules are paywalled, but the mechanism
description itself (open at/below rolling N-day low of opens, close above
open, hold close->next-open only) is fully specified and directly
implementable.

This is distinct from every other N-day-low strategy already in this repo's
knowledge base (Double 7s 2026-09-04-114 uses close vs N-day low of closes
with a signal-based exit and SMA200 trend filter; 5-Day-Low-of-Range
2026-09-07-005 uses IBS<0.25 + close<5-day-low-of-CLOSES with a fixed
multi-day time-stop hold; Turtle Soup 2026-09-04-076 fades a failed
breakdown on the NEXT close). None combine: (a) the OPEN specifically at an
N-day low, (b) an intraday bullish reversal (close>open) as the trigger, and
(c) a single-bar OVERNIGHT-ONLY hold (close-to-next-open), which is a
structurally different return-generation mechanism than every other
strategy file in this repo (which all realize returns close-to-close).

Signal logic
------------
- Trigger day (day i): today's OPEN <= the rolling min of the last
  `n_days` opens (including today) AND today's CLOSE > today's OPEN
  (bullish intraday reversal off a fresh low open).
- Position: long from day i's close through day i+1's open only (i.e. the
  overnight session). Flat all other times -- this strategy never holds
  through a full trading day.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1}, 1 on the day
        AFTER a trigger, representing "holding the overnight gap that ends
        at this bar's open")
    generate_returns(price_df, **params) -> pd.Series   (daily strategy
        returns, using close-to-next-open exposure, not close-to-close)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(price_df: pd.DataFrame, n_days: int = 5) -> pd.Series:
    """Return a {0,1} series: 1 on day i means "holding the overnight
    position that was entered at day i-1's close and exits at day i's
    open" -- i.e. the trigger fired on day i-1.
    """
    df = _prep(price_df)
    open_ = df["open"]
    close = df["close"]

    rolling_low_open = open_.rolling(n_days).min()
    trigger = (open_ <= rolling_low_open) & (close > open_)

    # Position on day i reflects a trigger that fired on day i-1 (shift by
    # one bar so the position series is knowable using only past info).
    position = trigger.shift(1).fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, n_days: int = 5) -> pd.Series:
    """Overnight (close[i-1] -> open[i]) returns, applied only on days
    where `generate_signals` indicates an active overnight position.
    """
    df = _prep(price_df)
    open_ = df["open"]
    close = df["close"]

    position = generate_signals(price_df, n_days=n_days)
    overnight_ret = (open_ / close.shift(1) - 1.0).fillna(0.0)
    strategy_ret = position * overnight_ret
    return strategy_ret
