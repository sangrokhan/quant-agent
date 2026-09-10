"""Strategy: Plain 13-period Elder Force Index zero-line crossover, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-097):
Per Google AI-overview synthesis (Definedge Securities, StockCharts.com
ChartSchool, Deepvue -- via browser_exec fallback, standard web_search
result for this query), the disclosed rule: Raw Force Index (1-period) =
(today's close - yesterday's close) * today's volume; a 13-period EMA of
this raw series is the standard "trend filter" reading -- when the 13-period
Force Index is above zero, bulls control the medium-term trend (buy
opportunities only); when it crosses below zero, bears take control. The
simplest disclosed mechanical rule is a straight zero-line crossover: buy
when the 13-period Force Index crosses above zero, exit (or short, adapted
here long-only per this repo's established convention) when it crosses back
below zero.

This is a genuinely new, simpler Force Index variant distinct from every
other Force Index strategy already in this repo:
- 2026-09-04-049: dual-EMA (13-period trend filter + 2-3 period pullback
  timing trigger) -- two lines, pullback-buy logic, not a plain crossover.
- 2026-09-05-048: FI(39) bullish price/indicator DIVERGENCE detection, a
  completely different signal mechanism (swing-low comparison).
- 2026-09-09-086: 2-period FI zero-cross combined with a Schaff Trend Cycle
  (STC) confirmation filter -- adds a second, unrelated indicator.
This strategy isolates the single most basic form (one EMA period, zero-line
cross, no secondary confirmation/pullback logic) to test whether the added
complexity in the other three variants was actually earning its keep, or
whether the plain rule already works (or fails) on its own.

Signal logic
------------
- Raw Force Index: FI_raw[t] = (close[t] - close[t-1]) * volume[t]
- Force Index (fi_period): EMA(FI_raw, fi_period), default 13 (source's own
  standard "trend filter" period).
- Entry (long): FI crosses from <=0 to >0 (bulls take control).
- Exit: FI crosses from >0 to <=0 (bears take control), or max_hold_days
  elapses (safety backstop; source's own rule has no time-stop, but every
  other strategy in this repo uses one to bound holding risk).
- Long-only, flat otherwise, no re-entry while already in a position.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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
    fi_period: int = 13,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    fi_raw = (close - close.shift(1)) * volume
    fi = fi_raw.ewm(span=fi_period, adjust=False).mean()

    prev_fi = fi.shift(1)
    cross_above = (prev_fi <= 0) & (fi > 0)
    cross_below = (prev_fi > 0) & (fi <= 0)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(cross_below.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(cross_above.iloc[i]):
                in_position = True
                entry_idx = i
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
