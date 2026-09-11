"""Strategy: Bullish Hikkake Pattern (inside-bar false breakdown reversal).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-087):
Per QuantifiedStrategies.com's own disclosed definition
(https://www.quantifiedstrategies.com/bullish-hikkake-pattern/, "Meaning,
definition and backtest Analysis" article -- no numeric backtest stats
disclosed on the page itself, but the pattern's mechanical definition is
precise and directly implementable): the Bullish Hikkake is a multi-candle
"fakey"/false-breakout pattern:

  1. Day 1-2 form an inside bar / harami: Day 2's high < Day 1's high AND
     Day 2's low > Day 1's low (Day 2 fully contained within Day 1's range).
  2. A subsequent day (the "fake breakdown" day) breaks BELOW the inside
     bar's low (Day 2's low), enticing bearish traders to short with a
     stop above the inside bar's high -- this is the "trap".
  3. Within a short confirmation window after the fake breakdown, price
     reverses and closes ABOVE the inside bar's high (Day 2's high),
     triggering the trapped shorts' stops and confirming the bullish
     Hikkake signal -> long entry.

Source explicitly states: "It is like a three inside down candlestick
pattern but without the constraints -- it doesn't require a specific type
of trend, and the candle color doesn't matter", and describes the
false-breakdown -> stop-hunt -> reversal mechanism as the causal
rationale (short-covering fuel for the up-move). First Hikkake-pattern
strategy in this repo -- distinct from all prior candlestick patterns
(three inside up/down, engulfing, morning star, etc. -- keyword search of
strategies_index.jsonl for "hikkake" returned 0 prior matches).

Because the source gives no numeric confirmation-window/exit rule, we
grid-test the confirmation window (how many days after the fake breakdown
the upside breakout must occur) and the exit rule (fixed time-stop) as the
tunable parameters, per RESEARCH_LOOP.md guidance to ground hypotheses in
what was actually read while still needing to specify implementation
details the source left open.

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
    confirm_window: int = 3,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    confirm_window: max number of bars after the fake-breakdown day within
        which the close must break above the inside bar's high to confirm
        the bullish Hikkake signal (source gives no numeric window; this
        is the primary tunable grid-tested here).
    max_hold_days: fixed time-stop once a confirmed long entry is taken
        (source doesn't disclose an exit rule for this pattern either).
    """
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]
    n = len(df)

    # Inside bar (harami): bar i is inside bar i-1.
    inside_bar = (high < high.shift(1)) & (low > low.shift(1))
    inside_high = high.shift(1).where(inside_bar)  # = Day1 high = Day2's containing range high... 
    # Actually the inside bar itself (Day2) defines the range to break: use Day2's own high/low.
    ib_high = high.where(inside_bar)
    ib_low = low.where(inside_bar)

    buy = pd.Series(False, index=close.index)
    # For each inside-bar day, look forward for a fake breakdown (low < ib_low)
    # followed within confirm_window days by a close > ib_high.
    ib_idx_positions = [i for i in range(n) if bool(inside_bar.iloc[i])]
    for ib_pos in ib_idx_positions:
        this_ib_high = ib_high.iloc[ib_pos]
        this_ib_low = ib_low.iloc[ib_pos]
        if pd.isna(this_ib_high) or pd.isna(this_ib_low):
            continue
        # search forward up to confirm_window+1 bars after the inside bar
        # for a fake breakdown day (low < ib_low), then confirmation.
        breakdown_pos = None
        search_end = min(n, ib_pos + 1 + confirm_window + 1)
        for j in range(ib_pos + 1, search_end):
            if low.iloc[j] < this_ib_low:
                breakdown_pos = j
                break
        if breakdown_pos is None:
            continue
        confirm_end = min(n, breakdown_pos + 1 + confirm_window)
        for k in range(breakdown_pos + 1, confirm_end):
            if close.iloc[k] > this_ib_high:
                buy.iloc[k] = True
                break

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(buy.iloc[i]):
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
