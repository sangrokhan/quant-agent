"""Strategy: ATR-band breakout-from-open, with overnight carry gated by the
same day's intraday breakout direction (long-only variant).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per Concretum Group's "Breaking the Rules of Intraday Trading" research note
(https://concretumgroup.com/breaking-the-rules-of-intraday-trading/), a
plain-vanilla SPY intraday-trend strategy (enter long when price breaks
above an ATR-band around the session open, exit at end of day) sees its
long-side performance improve decisively when the end-of-day position is
carried overnight into the next session's open, because of the well
documented overnight-return risk premium in equities (the short side shows
the opposite effect -- overnight carry hurts shorts -- confirming the
premium is a long-only phenomenon, not generic serial correlation). The
source's own hybrid variant (hold overnight ONLY when the EOD position is
long) lifted gross Sharpe from 0.88 to ~1.07 and CAGR from 14.1% to ~20%
on SPY 2006-2026.

Adapted here as a long-only daily-bar strategy (this repo only has daily
OHLCV via data/loaders.py, not intraday bars, so the "ATR-band breakout
from the session open" signal is proxied at daily granularity: a bullish
breakout day is one where the close finishes more than `atr_mult` ATRs
above that same day's open). On a breakout day, the strategy captures BOTH
the intraday move (open->close, proxied since we lack true intraday
tick-level entries) AND continues holding overnight into the next day's
open (close->next_open), stacking the intraday-trend edge with the
overnight-premium edge described in the source -- distinct from this
repo's existing overnight-hold family (all of which gate the overnight
decision on an EXTERNAL trend/VIX/volume filter measured as of the prior
close) since here the gate is the CURRENT day's own realized intraday
breakout, known only at that day's close.

Interface contract for validators (see validation/validators.py) /
grid_test.py (see validation/grid_test.py):
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


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def generate_signals(
    price_df: pd.DataFrame,
    atr_period: int = 14,
    atr_mult: float = 0.5,
) -> pd.Series:
    """Return {0,1}: 1 = a bullish intraday breakout day (close finished
    atr_mult*ATR above that day's own open). This is both the intraday
    exposure flag AND (via generate_returns) the gate for holding
    overnight into the next day's open.
    """
    df = _prep(price_df)
    atr = _atr(df, atr_period)
    breakout_threshold = df["open"] + atr_mult * atr
    is_breakout_day = (df["close"] > breakout_threshold).fillna(False)
    return is_breakout_day.astype(int).rename("position")


def generate_returns(
    price_df: pd.DataFrame,
    atr_period: int = 14,
    atr_mult: float = 0.5,
) -> pd.Series:
    df = _prep(price_df)
    breakout = generate_signals(df, atr_period=atr_period, atr_mult=atr_mult)

    open_ = df["open"]
    close = df["close"]

    # Intraday leg: only realized on a breakout day (open[t] -> close[t]).
    intraday_ret = (close / open_ - 1.0).fillna(0.0)
    intraday_component = breakout * intraday_ret

    # Overnight leg: carried into day t+1's open ONLY if day t was a
    # breakout day (the gate from the source's hybrid variant). This return
    # accrues to day t+1 (close[t] -> open[t+1]).
    overnight_ret = (open_.shift(-1) / close - 1.0).fillna(0.0)
    overnight_component = breakout * overnight_ret
    # Shift the overnight component forward by one bar so it lands on the
    # day it's actually realized (day t+1), matching daily-return alignment.
    overnight_component = overnight_component.shift(1).fillna(0.0)

    total_ret = intraday_component + overnight_component
    return total_ret.rename("returns")
