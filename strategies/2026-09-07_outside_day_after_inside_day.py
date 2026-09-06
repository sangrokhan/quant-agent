"""Strategy: Outside Day After Inside Day (HHLL-style mean-reversion setup).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-008):
Per QuantifiedStrategies.com's disclosed rule (via social-media summaries
of their DIA study, since the full blog article 404s but the mechanical
rule is stated verbatim across their own Facebook/X/Instagram/LinkedIn
posts): "DIA just printed an outside day after an inside day, triggering
a simple mean-reversion setup... I tested a simple rule: buy DIA at the
next open after this pattern appears. Since 1998: 125 trades, 76% win
rate." This is the mechanical realization of the more general HHLL
(Higher-High-Lower-Low) price-action reversal concept (source's own
"HHLL Trading Strategy" article: "That said, the HH and LL constitute
what is called an outside day").

Rule: an inside day (today's high < yesterday's high AND today's low >
yesterday's low) immediately followed by an outside day (today's high >
yesterday's high AND today's low < yesterday's low, i.e. today's range
fully engulfs yesterday's) triggers a long entry at the NEXT bar's open
(source's own stated execution: "buy at the next open after this pattern
appears"). Exit after a fixed holding period (source doesn't disclose an
exact day count in the public summaries; this repo tests a small
max_hold_days grid per its standard practice, since the pattern is
economically a short-term mean-reversion snap-back after a 2-day
volatility expansion).

Distinct from every candlestick-pattern strategy already tested in this
repo: this is a specific TWO-BAR SEQUENCE (inside day immediately
followed by outside day), not a single-bar pattern (Harami, Engulfing,
Piercing Line) nor the single inside-day pullback tested in
2026-09-07-006/007 (which required an inside day + a PRIOR gap-down, not
a following outside day).

Signal logic
------------
- Inside day on day t-1: high[t-1] < high[t-2] AND low[t-1] > low[t-2].
- Outside day on day t: high[t] > high[t-1] AND low[t] < low[t-1].
- Trigger on day t (inside day immediately followed by outside day).
- Entry: long at the OPEN of day t+1 (source's stated execution point).
  Approximated here (no separate open-based entry price bookkeeping
  needed for the returns-based backtest) by using close-to-close returns
  starting from day t+1's close (i.e. position becomes 1 as of day t+1),
  consistent with this repo's standard generate_returns shift convention.
- Exit: fixed holding period of `hold_days` trading days from entry.
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and
grid_test.py: generate_signals/generate_returns take price_df plus keyword
params.
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
    hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high, low = df["high"], df["low"]

    inside_day = (high < high.shift(1)) & (low > low.shift(1))
    outside_day = (high > high.shift(1)) & (low < low.shift(1))

    # Trigger: inside day on t-1, outside day on t.
    trigger = (inside_day.shift(1) & outside_day).fillna(False)

    # Entry executes at the NEXT bar's open -> position turns on starting
    # the bar AFTER the trigger bar (shift trigger forward by 1 day).
    entry = trigger.shift(1).fillna(False)

    entry_arr = entry.to_numpy()
    position = pd.Series(0, index=df.index, dtype=int)
    pos_arr = position.to_numpy().copy()

    in_pos = False
    hold_counter = 0

    for i in range(len(df)):
        if in_pos:
            hold_counter += 1
            if hold_counter >= hold_days:
                in_pos = False
                hold_counter = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if entry_arr[i]:
                in_pos = True
                hold_counter = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    hold_days: int = 5,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(price_df, hold_days=hold_days)
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
