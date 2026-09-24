"""Strategy: Bulkowski Shark-32 chart pattern, trend-continuation (both
long and short sides), traded with the inbound price trend per the
source's own explicit trading tactic.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/Shark32.html (Thomas Bulkowski,
browser_exec fallback -- web_search's DDGS backend cannot usefully extract
this domain, as with every prior thepatternsite.com entry this cron
trigger).

Source's own disclosed identification rules and statistics:
    "3 days: The shark-32 pattern is a three bar pattern. Shape: Look for
    two consecutively lower highs and higher lows [two consecutive inside
    days]. Last Bar: cannot be a four price doji."
    "Continuation: The pattern acts as a continuation 60% of the time."
    "Trade with the trend: Since the shark-32 acts as a continuation
    pattern, expect the breakout to be in the same direction as the
    inbound price trend."
    "Breakout: Wait for price to either close above the top or below the
    bottom of the pattern before taking a position."
    Overall performance rank: 18/23 (small patterns with upward
    breakouts in a bull market). Break-even failure rate: 32% (up
    breakouts). Average rise: 11%. Percentage meeting price target: 72%
    (a 2x-pattern-height Measure Rule target, source's own disclosed
    testing methodology: "Entry: buy stop a penny above the pattern top.
    Loss Exit: stop loss a penny below the pattern bottom. Target exit:
    limit order at twice the pattern height added to the top price.").

This strategy implements the source's own explicit "trade with the trend"
tactic directly: long entries only when the pattern's inbound trend
(measured by an SMA slope filter) is upward AND breakout is upward; short
entries only when the inbound trend is downward AND breakout is downward
-- i.e. only continuation-direction trades are taken (the source's own
60%-continuation statistic is a description of unconditional behavior;
this strategy filters FOR the continuation direction using the trend
filter, rather than taking both directions blind). Exit uses the source's
own disclosed Measure Rule (2x pattern height target) and pattern-boundary
stop-loss, plus a time-stop.

First "Shark-32" strategy in this repo (0 prior index hits) -- distinct
from every other 3-bar pattern already tested (e.g. inside-day
compression breakout strategies use a SINGLE inside day; Shark-32
explicitly requires exactly TWO CONSECUTIVE inside days, a stricter and
structurally distinct 3-bar shape).

Signal logic (numeric proxy for the source's disclosed identification
guidelines + trading tactics)
------------------------------------------------------------------------
1. Two consecutive inside days ending at bar t (bars t-2, t-1, t): bar
   t-1's high < bar t-2's high AND bar t-1's low > bar t-2's low
   (candle 2 inside candle 1); bar t's high < bar t-1's high AND bar t's
   low > bar t-1's low (candle 3 inside candle 2). Bar t is not a
   four-price doji (open != high or high != low, i.e. some real range).
2. Inbound trend direction (source's own disclosed "trade with the
   trend" tactic): close[t-2] relative to SMA(trend_window) evaluated at
   the pattern's first bar -- uptrend if above, downtrend if below.
3. Breakout/entry: long entry (in an uptrend) on the first subsequent bar
   whose close exceeds the pattern's high (max of bars t-2..t); short
   entry (in a downtrend) on the first subsequent bar whose close is
   below the pattern's low (min of bars t-2..t). Off-trend breakouts
   (counter-trend) are NOT traded, per the source's own tactic.
4. Exit: source's own Measure Rule (height = pattern_high - pattern_low,
   target = breakout_price +/- height * target_mult) OR price closes back
   through the opposite pattern boundary (failed breakout stop-loss) OR
   a max_hold_days time-stop, whichever comes first.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({-1,0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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
    trend_window: int = 20,
    target_mult: float = 2.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {-1, 0, 1} position series for Shark-32 pattern
    completions, traded only in the direction of the inbound trend."""
    df = _prep(price_df)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    n = len(c)

    sma = c.rolling(trend_window).mean()

    o_a = o.to_numpy()
    h_a = h.to_numpy()
    l_a = l.to_numpy()
    c_a = c.to_numpy()
    sma_a = sma.to_numpy()

    entries: dict[int, tuple[int, float, float, float]] = {}
    # entries[j] = (direction, target_price, stop_price, pattern_high/low ref)

    for t in range(2, n):
        a, b, e = t - 2, t - 1, t
        inside1 = (h_a[b] < h_a[a]) and (l_a[b] > l_a[a])
        inside2 = (h_a[e] < h_a[b]) and (l_a[e] > l_a[b])
        if not (inside1 and inside2):
            continue
        # not a four-price doji on the last bar
        if h_a[e] == l_a[e]:
            continue
        if np.isnan(sma_a[a]):
            continue

        pattern_high = max(h_a[a], h_a[b], h_a[e])
        pattern_low = min(l_a[a], l_a[b], l_a[e])
        height = pattern_high - pattern_low
        if height <= 0:
            continue

        uptrend = c_a[a] > sma_a[a]

        if uptrend:
            direction = 1
            for j in range(e + 1, n):
                if c_a[j] > pattern_high:
                    if j not in entries:
                        target_price = pattern_high + height * target_mult
                        stop_price = pattern_low
                        entries[j] = (direction, target_price, stop_price, pattern_high)
                    break
        else:
            direction = -1
            for j in range(e + 1, n):
                if c_a[j] < pattern_low:
                    if j not in entries:
                        target_price = pattern_low - height * target_mult
                        stop_price = pattern_high
                        entries[j] = (direction, target_price, stop_price, pattern_low)
                    break

    position = np.zeros(n, dtype=int)
    in_pos = False
    entry_idx = -1
    direction = 0
    target_price = 0.0
    stop_price = 0.0

    for t in range(n):
        if not in_pos and t in entries:
            direction, target_price, stop_price, _ref = entries[t]
            in_pos = True
            entry_idx = t
        if in_pos:
            position[t] = direction
            held = t - entry_idx
            if direction == 1:
                hit_target = c_a[t] >= target_price
                hit_stop = c_a[t] < stop_price
            else:
                hit_target = c_a[t] <= target_price
                hit_stop = c_a[t] > stop_price
            if hit_target or hit_stop or held >= max_hold_days:
                in_pos = False

    return pd.Series(position, index=c.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs). Short
    positions (-1) profit when price falls."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
