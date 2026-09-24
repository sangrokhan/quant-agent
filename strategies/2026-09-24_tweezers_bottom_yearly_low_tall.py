"""Strategy: Bulkowski Tweezers Bottom candlestick, filtered by the source's
own disclosed performance-boosting refinements (near yearly low + tall
candles), long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/TweezersBottom.html (Thomas
Bulkowski, browser_exec fallback -- web_search's DDGS backend cannot
usefully extract this domain, as with every prior thepatternsite.com entry
this cron trigger).

Source's own disclosed identification rules and statistics:
    "Price trends downward leading to the start of the tweezers. There,
    two candles of any color share the same low price... It is supposed
    to be a bullish reversal because price stops at the same low twice,
    signaling a support area, but testing reveals that price just
    continues lower [52% of the time, near random]."
    Theoretical performance: bullish reversal.
    Tested performance: bearish continuation 52% of the time (near-random
    baseline -- source explicitly warns "do not depend on predicting the
    breakout direction" on the raw/unfiltered pattern).
    Overall performance rank (unfiltered): 44/103 -- mediocre.

Critically, the source's own "Three Trading Tidbits" (book p.832/834)
disclose THREE numeric refinements that the raw pattern lacks:
    1. "Tweezers bottom candles that appear within a third of the yearly
       low perform best" -- p.832.
    2. "Select tall candles for the best performance" -- p.832.
    3. "Tweezers bottoms within a third of the yearly high tend to act as
       reversals most often" -- p.834 (i.e. near yearly LOW, the source
       still expects mixed/continuation behavior on average, but tallness
       + proximity to the low is the source's own disclosed best-performing
       subset, not this strategy's own invented filter).

This strategy trades exactly the source-disclosed refined subset (near
yearly low + tall candles) with the standard "closes above the top of the
tweezers pattern" breakout confirmation the source's own Example section
describes, rather than the raw/unfiltered near-random pattern -- the same
"trade the source's own preferred numeric refinement, not the weak
baseline" approach already used successfully for Above the Stomach
(2026-09-24-116) and Takuri Line (2026-09-24-117, rejected on feasibility
despite the same approach) earlier this cron trigger.

First "Tweezers Bottom" strategy in this repo (0 prior index hits) --
distinct from the "Matching Low" pattern already tested (6 prior index
hits) because Matching Low requires equal CLOSES with a specific tolerance
band, while Tweezers Bottom requires equal LOWS (the shadow/wick minimum),
a structurally different equality condition on a different price point.

Signal logic (numeric proxy for the source's disclosed identification
guidelines + Three Trading Tidbits refinements)
------------------------------------------------------------------------
1. Downtrend context (source's own required setup): close[t-1] <
   SMA(trend_window) evaluated at the first tweezers candle.
2. Two adjacent candles (t-1, t) whose lows match within `low_tol_pct`
   of each other (source's own "share the same low price" -- real markets
   rarely produce an exact tie, so a small tolerance band is the numeric
   proxy).
3. Yearly-low filter (source's own disclosed best-performing subset):
   the shared low sits within the bottom `yearly_low_third` fraction of
   the trailing `yearly_window`-day high-low range.
4. Tall-candle filter (source's own disclosed best-performing subset):
   at least one of the two tweezers candles has a real body
   (|close-open|) >= `tall_body_pct` of its own trading range (high-low),
   the standard "tall candle" proxy used elsewhere in this repo.
5. Confirmation/entry (source's own Example section): long entry on the
   first subsequent bar whose close exceeds the top of the tweezers
   pattern (max high of the two tweezers candles).
6. Exit: Measure Rule target (formation height = pattern top - shared low,
   target = breakout_price + height * target_pct) OR close falls back
   below the shared tweezers low (failed breakout stop-loss) OR a
   max_hold_days time-stop, whichever comes first.

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
    low_tol_pct: float = 0.003,
    yearly_window: int = 252,
    yearly_low_third: float = 0.33,
    tall_body_pct: float = 0.5,
    target_pct: float = 0.5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series for Tweezers Bottom
    completions filtered to the source's disclosed best-performing subset
    (near yearly low + tall candle)."""
    df = _prep(price_df)
    open_, high, low, close = df["open"], df["high"], df["low"], df["close"]
    n = len(close)

    sma = close.rolling(trend_window).mean()
    roll_high = high.rolling(yearly_window).max()
    roll_low = low.rolling(yearly_window).min()

    open_a = open_.to_numpy()
    high_a = high.to_numpy()
    low_a = low.to_numpy()
    close_a = close.to_numpy()
    sma_a = sma.to_numpy()
    rh_a = roll_high.to_numpy()
    rl_a = roll_low.to_numpy()

    entries: dict[int, tuple[float, float]] = {}

    for t in range(1, n):
        a, b = t - 1, t
        # downtrend context at the first candle
        if np.isnan(sma_a[a]) or close_a[a] >= sma_a[a]:
            continue
        # shared low, within tolerance
        lo_a, lo_b = low_a[a], low_a[b]
        base = min(lo_a, lo_b)
        if base <= 0:
            continue
        if abs(lo_a - lo_b) / base > low_tol_pct:
            continue
        shared_low = (lo_a + lo_b) / 2.0

        # yearly-low proximity filter
        if np.isnan(rh_a[a]) or np.isnan(rl_a[a]):
            continue
        yr_range = rh_a[a] - rl_a[a]
        if yr_range <= 0:
            continue
        pos_in_range = (shared_low - rl_a[a]) / yr_range
        if pos_in_range > yearly_low_third:
            continue

        # tall-candle filter: either candle's body >= tall_body_pct of its range
        def _tall(i: int) -> bool:
            rng = high_a[i] - low_a[i]
            if rng <= 0:
                return False
            body = abs(close_a[i] - open_a[i])
            return (body / rng) >= tall_body_pct

        if not (_tall(a) or _tall(b)):
            continue

        pattern_top = max(high_a[a], high_a[b])
        height = pattern_top - shared_low
        if height <= 0:
            continue
        target_price = pattern_top + height * target_pct
        stop_price = shared_low

        for j in range(b + 1, n):
            if close_a[j] > pattern_top:
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
            hit_target = close_a[t] >= target_price
            hit_stop = close_a[t] < stop_price
            if hit_target or hit_stop or held >= max_hold_days:
                in_pos = False

    return pd.Series(position, index=close.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
