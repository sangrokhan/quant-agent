"""Strategy: 3DC (3-day trend compression) pattern, long-only, traded in
the source-disclosed strongest context (downtrend reversal in stocks).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/3DC.html (Thomas Bulkowski's
write-up of Andrea Unger's "The Trend Compression Pattern," Technical
Analysis of Stocks & Commodities, February 2024; browser_exec fallback --
web_search's DDGS backend cannot usefully extract thepatternsite.com, as
with every prior entry from this domain this cron trigger).

Source's own disclosed identification rules and statistics:
    "3DC is a three-bar pattern. Shape: Add the height of the first two
    bars of the pattern. The third bar must be less than one-third of the
    total [sum(height1, height2)]. The position (above, below, or the
    same as the other price bars) of the three bars is irrelevant" (i.e.
    a pure volatility-compression condition on the 3rd bar's range
    relative to the sum of the prior two bars' ranges, with NO
    directional/overlap requirement -- distinct from inside-day
    compression, which requires strict high/low containment).
    "The 3DC pattern in stocks performs best if the inbound price trend
    is down (gains of $104.70 versus $83.91 for the benchmark)... That
    means reversals outperform 3DC patterns acting as continuation
    patterns" -- i.e. the source's own disclosed strongest context is
    specifically a DOWNTREND reversal in STOCKS (the source explicitly
    notes it "underperforms the benchmark in cryptocurrencies" and is
    "mediocre" in ETFs unless the inbound trend is UP, a different,
    weaker context this strategy does not target).
    Source's own disclosed testing methodology: "Entry: buy stop a penny
    above the pattern top. Stop loss: a penny below the pattern bottom.
    Target exit: twice the height of the 3DC added to the top of it."

This strategy targets exactly the source's own disclosed
strongest-performing combination: a 3DC compression pattern occurring
after a downtrend, trading the reversal (long) with the source's own
disclosed 2x-height Measure Rule target and pattern-boundary stop-loss.

First "3DC" strategy in this repo (0 prior index hits) -- distinct from
inside-day compression breakout strategies already tested (3DC's
compression condition is on bar RANGE/height only, with the position of
the third bar relative to the first two being explicitly irrelevant per
the source -- no containment requirement, unlike inside-day patterns
which require strict high/low containment within the prior bar).

Signal logic (numeric proxy for the source's disclosed identification
guidelines + testing methodology)
------------------------------------------------------------------------
1. Downtrend context (source's own disclosed strongest-performing
   context): close[t-2] < SMA(trend_window) evaluated at the pattern's
   first bar.
2. Compression shape: height1 = high[t-2]-low[t-2], height2 =
   high[t-1]-low[t-1], height3 = high[t]-low[t]; require
   height3 < compression_ratio * (height1 + height2) (source's own
   disclosed "less than one-third of the total," compression_ratio
   defaults to 1/3).
3. Confirmation/entry: long entry on the first subsequent bar whose close
   exceeds the pattern's high (max of the 3 bars) -- source's own
   disclosed "buy stop a penny above the pattern top" (approximated here
   with a close-above-high confirmation rather than an intrabar stop
   order, consistent with this repo's other pattern strategies).
4. Exit: source's own disclosed Measure Rule (height = pattern_high -
   pattern_low across all 3 bars, target = breakout_price + height *
   target_mult, source's own disclosed "twice the height... added to the
   top") OR close falls back below the pattern low (failed breakout
   stop-loss) OR a max_hold_days time-stop, whichever comes first.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
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
    compression_ratio: float = 1.0 / 3.0,
    target_mult: float = 2.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series for 3DC pattern
    completions, traded only after a downtrend (the source's own
    disclosed strongest-performing context)."""
    df = _prep(price_df)
    h, l, c = df["high"], df["low"], df["close"]
    n = len(c)

    sma = c.rolling(trend_window).mean()

    h_a = h.to_numpy()
    l_a = l.to_numpy()
    c_a = c.to_numpy()
    sma_a = sma.to_numpy()

    entries: dict[int, tuple[float, float]] = {}

    for t in range(2, n):
        a, mid, b = t - 2, t - 1, t
        if np.isnan(sma_a[a]) or c_a[a] >= sma_a[a]:
            continue

        height1 = h_a[a] - l_a[a]
        height2 = h_a[mid] - l_a[mid]
        height3 = h_a[b] - l_a[b]
        total12 = height1 + height2
        if total12 <= 0:
            continue
        if not (height3 < compression_ratio * total12):
            continue

        pattern_high = max(h_a[a], h_a[mid], h_a[b])
        pattern_low = min(l_a[a], l_a[mid], l_a[b])
        height = pattern_high - pattern_low
        if height <= 0:
            continue
        target_price = pattern_high + height * target_mult
        stop_price = pattern_low

        for j in range(b + 1, n):
            if c_a[j] > pattern_high:
                if j not in entries:
                    entries[j] = (target_price, stop_price)
                break

    position = np.zeros(n, dtype=int)
    in_pos = False
    entry_idx = -1
    target_price = np.inf
    stop_price = -np.inf

    for t in range(n):
        if not in_pos and t in entries:
            in_pos = True
            entry_idx = t
            target_price, stop_price = entries[t]
        if in_pos:
            position[t] = 1
            held = t - entry_idx
            hit_target = c_a[t] >= target_price
            hit_stop = c_a[t] < stop_price
            if hit_target or hit_stop or held >= max_hold_days:
                in_pos = False

    return pd.Series(position, index=c.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
