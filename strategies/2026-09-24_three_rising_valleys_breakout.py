"""Strategy: Bulkowski Three Rising Valleys bullish continuation breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from Google SERP snippets of https://thepatternsite.com/ThreeRisingValleys.html
(Thomas Bulkowski's "Encyclopedia of Chart Patterns"; page fetched directly
returned a 404, but the identification rule and confirmation logic were
disclosed verbatim in the search snippets, and corroborated by a second
independent source -- both read via browser_exec; web_search's DDGS
backend returned unrelated/garbage results this iteration):

    "Three Rising Valleys: Identification Guidelines: Shape, Look for
    three valleys -- the bottom of each valley must be above the prior
    one." (thepatternsite.com SERP snippet)

    "Look for 3 rising valleys, each valley must be above the prior one...
    On this chart, I show the three rising valleys pattern at 1, 2, 3."
    (thepatternsite.com Quiz page SERP snippet)

    "As the name suggests, the three rising valleys pattern consists of
    three valleys, each higher than the last (HL). You can see two peaks
    between these valleys." (trading.biz SERP snippet, corroborating)

    "Prices must close above the confirmation point before a trade is
    placed." (dokumen.pub Encyclopedia of Chart Patterns excerpt, SERP
    snippet -- Bulkowski's standard confirmation-point convention used
    across the book: the highest intervening peak between the valleys)

This pattern ranks #4 in a separately-confirmed Google AI-overview "Top 10
Continuations, Upward Breakouts, Bull Markets" summary of Bulkowski's own
published performance-rank tables (Cup with handle 54%, Rounded top 51%,
Three rising valleys 51%, Rectangle top 51%, Rounded bottom 48% average
rise) -- i.e. a comparably strong prior to this repo's just-accepted
Rectangle Top strategy (2026-09-24-099), and DISTINCT from every prior
pattern tested in this repo: it requires exactly 3 monotonically-rising
swing lows (not a converging/parallel trendline pair, not a
neckline-and-rebound structure like Double Bottom).

Signal logic
------------
1. Swing-low detection: this repo's standard N-bar centered
   local-minimum detector (swing_window).
2. Pattern detection: within a rolling `lookback_bars` window, find three
   consecutive swing lows L1 < L2 < L3 (chronologically) such that
   price(L2) > price(L1) and price(L3) > price(L2) (each valley strictly
   above the prior one, per the source's own rule).
3. Confirmation point: the highest intervening peak's close between L1
   and L3 (Bulkowski's standard "confirmation point" convention).
4. Entry: long the bar a close first exceeds the confirmation point after
   L3 is confirmed (source: "Prices must close above the confirmation
   point before a trade is placed").
5. Exit: close falls back below the pattern's lowest valley (L3, failed
   breakout), a fixed measured-move target (height = confirmation_point -
   L3's price, target = confirmation_point + height * target_pct, this
   repo's standard measured-move convention reused from the just-tested
   Rectangle Top strategy since Bulkowski applies the same Measure Rule
   family across his pattern catalog), or a max_hold_days time-stop,
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
    lookback_bars: int = 60,
    target_pct: float = 0.51,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    is_low = _swing_lows(close, swing_window)
    swing_idx = np.where(is_low.fillna(False).values)[0]
    n = len(close)
    close_arr = close.to_numpy()

    raw_confirm_signals = np.zeros(n, dtype=bool)
    confirm_points = np.full(n, np.nan)
    valley3_prices = np.full(n, np.nan)

    for j in range(2, len(swing_idx)):
        i3 = swing_idx[j]
        i2 = swing_idx[j - 1]
        i1 = swing_idx[j - 2]
        if i3 - i1 > lookback_bars:
            continue
        p1, p2, p3 = close_arr[i1], close_arr[i2], close_arr[i3]
        if p2 > p1 and p3 > p2:
            # valid three-rising-valleys pattern confirmed at i3.
            confirmation_point = close_arr[i1:i3 + 1].max()
            # Mark this pattern active starting the bar after i3, waiting
            # for the first close above confirmation_point.
            for t in range(i3 + 1, min(n, i3 + 1 + lookback_bars)):
                if close_arr[t] > confirmation_point:
                    raw_confirm_signals[t] = True
                    confirm_points[t] = confirmation_point
                    valley3_prices[t] = p3
                    break

    position = np.zeros(n, dtype=int)
    in_pos = False
    entry_bar = -1
    entry_confirm = np.nan
    entry_valley3 = np.nan
    target_price = np.nan

    for t in range(n):
        if raw_confirm_signals[t] and not in_pos:
            in_pos = True
            entry_bar = t
            entry_confirm = confirm_points[t]
            entry_valley3 = valley3_prices[t]
            height = entry_confirm - entry_valley3
            target_price = entry_confirm + height * target_pct if height > 0 else np.inf
        if in_pos:
            position[t] = 1
            held = t - entry_bar
            failed = close_arr[t] < entry_valley3
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
