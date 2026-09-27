"""Strategy: Bulkowski "Knots" support/target confirmation for Double Bottoms
(long-only bullish mirror of the source's double-top short-sale pattern).

Hypothesis (2026-09-27 KB entry, this iteration): Bulkowski's "Trading Knots"
(https://thepatternsite.com/TradingKnots.html, released 2020-09-28) finds
that after a Double Top breaks down, price tends to travel to the nearest
prior "knot" (a >=3-bar sideways congestion with heavy price-bar overlap)
found along the preceding uptrend, and if that knot sits near/at the
pattern's own confirmation price, the subsequent decline tends to meet or
exceed the pattern's own measured-move target 70% of the time (90/129
tests, source's own eyeballed count) -- source frames this as a short-sale
setup. Per SAFETY.md (long-only, no short-selling execution code), this
iteration implements the BULLISH MIRROR: after a Double Bottom breaks out
upward, if a "knot" (>=3-bar low-range congestion) sits near/at the
pattern's own confirmation price within the preceding DOWNTREND leading
into the bottom, the subsequent rally is hypothesized to meet or exceed the
pattern's own measured-move target with similarly elevated odds (mirroring
the source's own double-top mechanism symmetrically, per Bulkowski's own
convention elsewhere in this repo of bullish/bearish pattern mirroring,
e.g. Eve&Eve vs Adam&Adam double bottoms/tops). First "Knots" strategy in
this repo (0 prior KB hits) -- distinct from all other double-bottom
entries already tested (Eve&Eve, Ugly Double Bottom, Double Bottom Neckline
Breakout) since none of those require a prior KNOT congestion at the
confirmation-price level as an additional confirming filter.

Signal logic (adapted to daily-bar mechanical detection):
- Detect two swing lows (`pivot_window`-bar fractal lows) within
  `bottom_tolerance_pct` of each other, separated by an intervening swing
  high (the "confirmation price" = that intervening high).
- Confirmation: close breaks above the confirmation price (measured-move
  target = confirmation_price + (confirmation_price - min(low1, low2))).
- Knot filter: within the `knot_lookback`-bar downtrend leading into the
  first (earlier) low, require at least one >=3-bar window where the
  high-low range of all bars overlaps heavily (each bar's range within
  `knot_overlap_pct` of the window's own price range) AND that window's
  own price level is within `knot_price_tolerance_pct` of the confirmation
  price -- Bulkowski's own "near/at the bottom of the double top"
  criterion, mirrored here as "near/at the confirmation price".
- Entry: on the breakout-confirmation bar, if the knot filter passed.
- Exit: close reaching the measured-move target, OR a max_hold_days
  time-stop.

Interface contract for validators/grid_test (see RESEARCH_LOOP.md Step 5):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _find_swing_lows(low: pd.Series, window: int) -> pd.Series:
    """Boolean series: True where low[i] is the min of the window centered at i."""
    n = len(low)
    is_low = pd.Series(False, index=low.index)
    for i in range(window, n - window):
        seg = low.iloc[i - window : i + window + 1]
        if low.iloc[i] == seg.min():
            is_low.iloc[i] = True
    return is_low


def _find_swing_highs(high: pd.Series, window: int) -> pd.Series:
    n = len(high)
    is_high = pd.Series(False, index=high.index)
    for i in range(window, n - window):
        seg = high.iloc[i - window : i + window + 1]
        if high.iloc[i] == seg.max():
            is_high.iloc[i] = True
    return is_high


def _has_knot(
    high: pd.Series,
    low: pd.Series,
    start_idx: int,
    end_idx: int,
    confirmation_price: float,
    knot_min_bars: int,
    knot_overlap_pct: float,
    knot_price_tolerance_pct: float,
) -> bool:
    """Scan [start_idx, end_idx) for a >=knot_min_bars-bar congestion window
    whose price level is within tolerance of confirmation_price."""
    if end_idx - start_idx < knot_min_bars:
        return False
    for w_start in range(start_idx, end_idx - knot_min_bars + 1):
        w_end = w_start + knot_min_bars
        seg_high = high.iloc[w_start:w_end]
        seg_low = low.iloc[w_start:w_end]
        window_range = seg_high.max() - seg_low.min()
        if window_range <= 0:
            continue
        # Heavy overlap: every bar's own range must span a large fraction of
        # the window's full range (Bulkowski's "lots of overlap" criterion).
        overlaps = ((seg_high - seg_low) / window_range) >= knot_overlap_pct
        if not overlaps.all():
            continue
        window_mid = (seg_high.max() + seg_low.min()) / 2.0
        if confirmation_price == 0:
            continue
        if abs(window_mid - confirmation_price) / confirmation_price <= knot_price_tolerance_pct:
            return True
    return False


def generate_signals(
    price_df: pd.DataFrame,
    pivot_window: int = 5,
    bottom_tolerance_pct: float = 0.02,
    max_bottom_spacing: int = 60,
    knot_lookback: int = 90,
    knot_min_bars: int = 3,
    knot_overlap_pct: float = 0.5,
    knot_price_tolerance_pct: float = 0.03,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]
    n = len(df)

    swing_lows = _find_swing_lows(low, pivot_window)
    swing_highs = _find_swing_highs(high, pivot_window)

    low_idxs = [i for i in range(n) if swing_lows.iloc[i]]

    entries = {}  # entry_idx -> target_price
    for j in range(1, len(low_idxs)):
        i2 = low_idxs[j]
        # search for a prior low i1 within max_bottom_spacing bars
        for k in range(j - 1, -1, -1):
            i1 = low_idxs[k]
            if i2 - i1 > max_bottom_spacing:
                break
            low1, low2 = low.iloc[i1], low.iloc[i2]
            if low1 == 0:
                continue
            if abs(low1 - low2) / low1 > bottom_tolerance_pct:
                continue
            # intervening confirmation price = highest high between i1 and i2
            between = high.iloc[i1 : i2 + 1]
            if between.empty:
                continue
            confirmation_price = between.max()
            bottom_low = min(low1, low2)
            target = confirmation_price + (confirmation_price - bottom_low)

            # knot lookback window: bars leading INTO i1 (the downtrend
            # before the first bottom)
            know_start = max(0, i1 - knot_lookback)
            has_knot = _has_knot(
                high, low, know_start, i1, confirmation_price,
                knot_min_bars, knot_overlap_pct, knot_price_tolerance_pct,
            )
            if not has_knot:
                continue

            # find breakout bar: first close > confirmation_price after i2
            for b in range(i2 + 1, min(n, i2 + 1 + max_hold_days)):
                if close.iloc[b] > confirmation_price:
                    entries[b] = target
                    break
            break  # only use the closest prior low for this i2

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    target_price = None
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if close.iloc[i] >= target_price or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if i in entries:
                in_position = True
                entry_idx = i
                target_price = entries[i]
                position.iloc[i] = 1
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
