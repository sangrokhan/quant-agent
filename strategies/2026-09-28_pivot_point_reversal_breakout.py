"""Strategy: Bulkowski "Pivot Point Reversal, Downtrend" traded in the
breakout (long) direction with a measured-move target exit.

Hypothesis (see knowledge_base/strategies_log.jsonl for the id):
Per Bulkowski (thepatternsite.com/PPRD.html, read 2026-09-28 via
browser_exec): a simple 2-bar pattern in a short-term downtrend where
today's close is above yesterday's high (a sharp one-day reversal-style
overshoot of the prior bar's entire range). Source's own finding
(consistent with this repo's already-accepted Key Reversal and Hook
Reversal patterns): despite being framed as a "reversal" pattern, it only
acts as a genuine trend reversal 31% of the time in a bull market -- so,
per this repo's established convention for these Bulkowski reversal-named
patterns (trade the DISCLOSED breakout direction, not the "reversal"
framing), this strategy trades upward breakouts (which the source's own
"Bull market, up breakout" row shows was profitable overall: net
profit/loss $71.03, 56% win rate, 5,515 winning trades out of 9,807 total
in that slice). Source's own measure rule (height of the 2-bar pattern
added to the high) hits the target 77% of the time in bull markets --
notably HIGHER than every other small pattern already tested this
trigger (2-Tall 42%, One-Day-Reversal-Bottom 73%, WRDUR 40%).

Distinct from this repo's already-accepted Key Reversal ("today's close >
prior day's high AND today's open < prior day's close", 2026-09-26-052)
and Hook Reversal (inside-day + edge-position filter) patterns: Pivot
Point Reversal has NO open-position constraint at all -- purely
close(t) > high(t-1), the simplest/loosest of this 2-bar-reversal family,
making it a useful "does the added complexity of Key/Hook actually help"
comparison point.

Signal logic
------------
- Downtrend filter: close(t-1) < close(t-1-trend_lookback) (short-term
  downtrend proxy, matching this trigger's other Bulkowski small-pattern
  strategies' 5-day-back convention).
- Qualifying bar: close(t) > high(t-1).
- Entry: next bar's exposure (source: "buy... at the open the next day",
  operationalized via this repo's standard 1-bar-shift generate_returns
  convention, so position is set starting the bar the condition is
  detected -- shift(1) in generate_returns then naturally delays actual
  P&L capture to the following bar's return, matching the source's own
  intent).
- Stop-loss: close drops below the pattern's own low (min(low(t-1),
  low(t))).
- Target: pattern high (max(high(t-1), high(t))) + measure_rule_mult *
  pattern height (source's own measure rule, 77%-hit).
- Time-stop: max_hold_days safety exit.

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
    trend_lookback: int = 5,
    measure_rule_mult: float = 1.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    n = len(close)
    qualifies = pd.Series(False, index=close.index)
    pat_top = pd.Series(index=close.index, dtype=float)
    pat_bottom = pd.Series(index=close.index, dtype=float)

    for i in range(trend_lookback + 1, n):
        if not (close.iloc[i - 1] < close.iloc[i - 1 - trend_lookback]):
            continue
        if not (close.iloc[i] > high.iloc[i - 1]):
            continue
        qualifies.iloc[i] = True
        pat_top.iloc[i] = max(high.iloc[i - 1], high.iloc[i])
        pat_bottom.iloc[i] = min(low.iloc[i - 1], low.iloc[i])

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop = target = None
    pending_top = pending_bottom = None
    pending_since = -1

    for i in range(n):
        if qualifies.iloc[i]:
            pending_top = pat_top.iloc[i]
            pending_bottom = pat_bottom.iloc[i]
            pending_since = i

        if in_position:
            held = i - entry_idx
            c = close.iloc[i]
            if c <= stop or c >= target or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if pending_top is not None and i == pending_since + 1:
                in_position = True
                entry_idx = i
                stop = pending_bottom
                target = pending_top + measure_rule_mult * (pending_top - pending_bottom)
                position.iloc[i] = 1
                pending_top = pending_bottom = None
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
