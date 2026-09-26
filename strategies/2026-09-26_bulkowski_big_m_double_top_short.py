"""Strategy: Bulkowski "Big M" (deep-drop double top) short pattern, daily bars.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-26-XXX):
Per Thomas Bulkowski's ThePatternSite.com analysis of the "Big M" pattern
(https://thepatternsite.com/bigm.html, browser_exec fallback -- web_search
DDGS backend returned empty/error results on multiple queries this
iteration), the Big M is a STRICTER variant of the ordinary double top,
distinguished by two extra numeric requirements the source itself calls
out ("tall sides"):
  - Twin peaks within tall_peak_tolerance_pct (source: <4%) of each other
    in price (a genuine double top, not just any local high pair).
  - The DROP between the two peaks (peak height to the intervening
    valley) is >= min_drop_pct (source: 10-20%+) -- this is what makes
    the pattern's "sides" tall/dramatic, distinguishing it from a shallow
    double top where the pullback between tops is minor.
  - Confirms as valid when price closes below the lowest valley between
    the two tops (standard double-top confirmation).

Source's own disclosed measure-rule target: subtract the pattern height
(peak to valley) from the confirmation price to get a downside target
(source explicitly offers a "closer" alternative using HALF the height
instead of the full height, selectable via a `use_half_height_target`
param here).

First "Big M" pattern tested in this repo (0 prior hits); distinct from:
- Plain Double Top (implicit in various triple-top/pattern entries):
  no minimum inter-peak drop-depth requirement.
- Cat's Ears (2026-09-24-111): a double-top-in-a-DOWNTREND continuation
  pattern with an RSI filter, structurally different context (Big M
  requires an UPWARD price trend leading into the pattern, i.e. it's a
  reversal-of-uptrend pattern, not a downtrend continuation).
- Double Top Setup (2026-09-24-139): tests time-symmetry between the
  rise into the pattern and the decline out of it, not a depth/tolerance
  filter on the peaks themselves.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (position: -1 short/0 flat)
    generate_returns(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _find_swing_highs(high: pd.Series, window: int) -> pd.Series:
    roll_max = high.rolling(2 * window + 1, center=True).max()
    return (high == roll_max) & high.notna()


def generate_signals(
    price_df: pd.DataFrame,
    peak_window: int = 8,
    tall_peak_tolerance_pct: float = 0.04,
    min_drop_pct: float = 0.10,
    prior_uptrend_lookback: int = 40,
    target_height_frac: float = 1.0,
    use_half_height_target: bool = False,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {-1, 0} short/flat position series.

    Scans for two swing highs within tall_peak_tolerance_pct of each other,
    with a >= min_drop_pct decline into the intervening valley, preceded
    by an upward price trend (close prior_uptrend_lookback bars before the
    first peak is below the first peak's high -- i.e. price rose into the
    pattern). Short entry confirms on the first close below the intervening
    valley low after the second peak.
    """
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]
    n = len(close)

    is_swing_high = _find_swing_highs(high, peak_window)
    swing_idxs = [i for i in range(n) if bool(is_swing_high.iloc[i])]

    short_trigger = pd.Series(False, index=close.index)
    stop_level = pd.Series(index=close.index, dtype=float)
    target_level = pd.Series(index=close.index, dtype=float)

    for a in range(len(swing_idxs) - 1):
        i1, i2 = swing_idxs[a], swing_idxs[a + 1]
        if i2 - i1 < peak_window:
            continue
        h1, h2 = high.iloc[i1], high.iloc[i2]
        if h1 <= 0:
            continue
        peaks_close = abs(h1 - h2) / h1 <= tall_peak_tolerance_pct

        valley_low = low.iloc[i1:i2 + 1].min()
        avg_peak = (h1 + h2) / 2.0
        drop_pct = (avg_peak - valley_low) / avg_peak if avg_peak > 0 else 0.0
        tall_sides = drop_pct >= min_drop_pct

        # Prior uptrend: price rose into peak 1 over prior_uptrend_lookback bars.
        lookback_start = max(0, i1 - prior_uptrend_lookback)
        prior_uptrend = close.iloc[lookback_start] < h1 if i1 > 0 else False

        if not (peaks_close and tall_sides and prior_uptrend):
            continue

        pattern_height = avg_peak - valley_low
        if pattern_height <= 0:
            continue

        search_end = min(n, i2 + 1 + 60)
        for j in range(i2 + 1, search_end):
            if close.iloc[j] < valley_low:
                short_trigger.iloc[j] = True
                stop_level.iloc[j] = max(h1, h2)
                eff_height = pattern_height * (0.5 if use_half_height_target else target_height_frac)
                target_level.iloc[j] = close.iloc[j] - eff_height
                break
            if high.iloc[j] > max(h1, h2) * 1.02:
                break  # invalidated by a fresh higher high

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    hold_days_left = 0
    stop_price = None
    target_price = None

    for i in range(n):
        if in_position:
            hit_stop = high.iloc[i] >= stop_price
            hit_target = low.iloc[i] <= target_price
            hold_days_left -= 1
            if hit_stop or hit_target or hold_days_left <= 0:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = -1
            continue

        if bool(short_trigger.iloc[i]):
            in_position = True
            stop_price = stop_level.iloc[i]
            target_price = target_level.iloc[i]
            hold_days_left = max_hold_days
            position.iloc[i] = -1
            continue

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
