"""Strategy: Bulkowski Eve & Eve Double Bottom (classic W) breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/eedb.html (Thomas Bulkowski's
"Encyclopedia of Chart Patterns" stats page; read via browser_exec after
web_search's DDGS backend returned unrelated/garbage results this
iteration). Source's own disclosed statistics and PRECISE numeric
identification rules (distinct from this repo's already-rejected generic
Double Bottom entry, 2026-09-08-101, which used only a qualitative
"neckline" rule with no disclosed numeric tolerances):

    "Eve & Eve Double Bottoms: Important Bull Market Results: Overall
    performance rank (1 is best): 5 out of 39. Break even failure rate:
    12%. Average rise: 50%. ... Price trend: Downward leading to the
    pattern. Shape: Two distinct valleys that look similar. Eve bottoms
    are wide and more rounded appearing... Peak: The rise between bottoms
    should measure at least 10%... Bottom price: The price variation
    between bottoms is small, usually between 0% and 6%. The two valleys
    should appear to bottom near the same price... Separation: The twin
    valleys are several weeks apart with most falling in the 2 to 7 week
    range... Confirmation: The double bottom confirms as a true double
    bottom once price closes above the peak between the two valleys...
    Wait for confirmation -- price to close above the peak between the
    valleys... If you don't wait, there's a 48% chance that price will
    continue lower without confirming the double bottom."

Bulkowski ranks this pattern 5th of 39 -- among the strongest priors
sourced from his catalog this cron trigger (comparable to Rectangle Top
[4/39] and stronger than Three Rising Valleys' informal tie at 51% avg
rise). "Eve & Eve" is explicitly what Bulkowski calls "the classic double
bottom" most chartists mean by that term -- but THIS repo's generic Double
Bottom entry (2026-09-08-101, rejected) tested only a bare
lower-swing-lows-near-neckline concept with no disclosed numeric
tolerances for bottom-price variation, peak-rise minimum, or valley
separation window. This entry adds all three of Bulkowski's own disclosed
numeric constraints, making it a genuinely distinct, more precisely
specified test of the same underlying pattern family.

Signal logic
------------
1. Swing-low detection: this repo's standard N-bar centered
   local-minimum detector (swing_window).
2. Valid Eve & Eve candidate: two swing lows L1, L2 (chronologically)
   within `lookback_bars` such that:
   - bottom_variation = |price(L2) - price(L1)| / price(L1) <=
     max_bottom_variation (source's disclosed 0-6% tolerance)
   - separation (L2 - L1 in trading days) is within
     [min_separation_days, max_separation_days] (source's disclosed
     "2 to 7 week" range, ~10-35 trading days)
   - the intervening peak's rise from L1 is >= min_peak_rise_pct (source's
     disclosed >=10% minimum)
   - prior downtrend: close at L1 is below its own SMA(trend_lookback)
     (source: "Price trend: Downward leading to the pattern")
3. Confirmation point: the highest intervening close between L1 and L2
   (source's own "peak between the valleys" convention).
4. Entry: long the first bar a close exceeds the confirmation point after
   L2 (source's own confirmation rule).
5. Exit: source's own Measure Rule (height = confirmation_point - L2's
   price, target = confirmation_point + height * target_pct, source's
   own disclosed 65% "percentage meeting price target"), OR close falling
   back below L2 (failed breakout), OR a max_hold_days time-stop,
   whichever comes first.

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


def _swing_lows(close: pd.Series, swing_window: int = 5) -> pd.Series:
    roll_min = close.rolling(2 * swing_window + 1, center=True).min()
    return close == roll_min


def generate_signals(
    price_df: pd.DataFrame,
    swing_window: int = 5,
    max_bottom_variation: float = 0.06,
    min_separation_days: int = 10,
    max_separation_days: int = 35,
    min_peak_rise_pct: float = 0.10,
    trend_lookback: int = 50,
    target_pct: float = 0.65,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    close_arr = close.to_numpy()
    n = len(close_arr)

    sma_trend = close.rolling(trend_lookback).mean()
    sma_arr = sma_trend.to_numpy()

    is_low = _swing_lows(close, swing_window)
    swing_idx = np.where(is_low.fillna(False).values)[0]

    raw_confirm = np.zeros(n, dtype=bool)
    confirm_points = np.full(n, np.nan)
    l2_prices = np.full(n, np.nan)

    for j in range(1, len(swing_idx)):
        i2 = swing_idx[j]
        i1 = swing_idx[j - 1]
        sep = i2 - i1
        if not (min_separation_days <= sep <= max_separation_days):
            continue
        p1, p2 = close_arr[i1], close_arr[i2]
        if p1 <= 0:
            continue
        bottom_variation = abs(p2 - p1) / p1
        if bottom_variation > max_bottom_variation:
            continue
        intervening_peak = close_arr[i1:i2 + 1].max()
        peak_rise = (intervening_peak - min(p1, p2)) / min(p1, p2) if min(p1, p2) > 0 else 0.0
        if peak_rise < min_peak_rise_pct:
            continue
        if np.isnan(sma_arr[i1]) or close_arr[i1] >= sma_arr[i1]:
            continue  # prior downtrend filter failed
        confirmation_point = intervening_peak
        for t in range(i2 + 1, min(n, i2 + 1 + max_hold_days)):
            if close_arr[t] < min(p1, p2):
                break  # invalidated (broke below the lower of the two bottoms)
            if close_arr[t] > confirmation_point:
                raw_confirm[t] = True
                confirm_points[t] = confirmation_point
                l2_prices[t] = p2
                break

    position = np.zeros(n, dtype=int)
    in_pos = False
    entry_bar = -1
    entry_confirm = np.nan
    entry_l2 = np.nan
    target_price = np.nan

    for t in range(n):
        if raw_confirm[t] and not in_pos:
            in_pos = True
            entry_bar = t
            entry_confirm = confirm_points[t]
            entry_l2 = l2_prices[t]
            height = entry_confirm - entry_l2
            target_price = entry_confirm + height * target_pct if height > 0 else np.inf
        if in_pos:
            position[t] = 1
            held = t - entry_bar
            failed = close_arr[t] < entry_l2
            hit_target = close_arr[t] >= target_price
            if failed or hit_target or held >= max_hold_days:
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
