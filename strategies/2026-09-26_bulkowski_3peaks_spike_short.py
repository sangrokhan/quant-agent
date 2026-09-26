"""Strategy: Bulkowski "3-Peaks and Spike" bearish/short pattern, daily bars.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-26-XXX):
Per Thomas Bulkowski's ThePatternSite.com analysis of the "3-Peaks and
Spike" pattern (https://thepatternsite.com/MultiPeak2B.html, browser_exec
fallback -- web_search DDGS backend returned empty/error results on
multiple queries this iteration), a bearish multi-peak topping pattern
forms when:
  - Three peaks occur near the same price level (peaks 1, 2, 3).
  - A fourth peak (the "spike") rises well above the first three, with
    typically no intervening peak between peak 3 and the spike.
  - Peaks are separated by at least ~1 week (5 price bars) per source.
  - The first three peaks must NOT already confirm as their own triple
    top (price must not have closed below the lowest valley between
    peaks 1-3 before the spike forms) -- otherwise it's a different
    pattern.
  - CONFIRMATION (short entry trigger): price closes below the lowest low
    between the four peaks (source's own explicit rule; an upward
    breakout instead invalidates the pattern entirely, per source).

Source's own disclosed measure rule: pattern height = spike peak high -
confirmation-point low; multiply by the source's own disclosed
"percentage meeting price target" (~45% in the source's own backtest) to
get a downside target below the confirmation point. This strategy
implements a short entry on confirmation with a target sized as a
fraction of the pattern height below the confirmation low, a stop above
the spike peak, and a time-stop.

First "3-Peaks and Spike" pattern tested in this repo (0 prior hits);
distinct from every other multi-peak topping pattern already tested
(Triple Top 2026-09-09-045 requires 3 roughly-EQUAL peaks with no 4th
taller spike; Head-and-Shoulders variants require a single higher middle
peak, not three equal peaks followed by a taller 4th).

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
    """Boolean series marking local maxima over a +/- window bar range."""
    roll_max = high.rolling(2 * window + 1, center=True).max()
    return (high == roll_max) & high.notna()


def generate_signals(
    price_df: pd.DataFrame,
    peak_window: int = 5,
    peak_match_tolerance_pct: float = 0.03,
    spike_min_excess_pct: float = 0.03,
    target_height_frac: float = 0.45,
    atr_period: int = 14,
    atr_stop_mult: float = 1.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {-1, 0} short/flat position series.

    Simplified daily-bar approximation of the 4-peak structure: scan for
    3 swing highs within peak_match_tolerance_pct of each other, followed
    by a 4th swing high at least spike_min_excess_pct taller, with no
    intervening close below the peaks-1-3 valley before the spike. Short
    entry triggers when close breaks below the lowest low between the
    four peaks.
    """
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]
    n = len(close)

    is_swing_high = _find_swing_highs(high, peak_window)
    swing_idxs = [i for i in range(n) if bool(is_swing_high.iloc[i])]

    # Precompute per-bar-index short-entry triggers with associated stop/target.
    short_trigger = pd.Series(False, index=close.index)
    stop_level = pd.Series(index=close.index, dtype=float)
    target_level = pd.Series(index=close.index, dtype=float)
    confirm_low_level = pd.Series(index=close.index, dtype=float)

    for a in range(len(swing_idxs) - 3):
        i1, i2, i3, i4 = swing_idxs[a], swing_idxs[a + 1], swing_idxs[a + 2], swing_idxs[a + 3]
        if i4 - i1 < 3 * peak_window:
            continue
        h1, h2, h3, h4 = high.iloc[i1], high.iloc[i2], high.iloc[i3], high.iloc[i4]
        base_peaks = [h1, h2, h3]
        base_mean = sum(base_peaks) / 3.0
        if base_mean <= 0:
            continue
        peaks_similar = all(abs(p - base_mean) / base_mean <= peak_match_tolerance_pct for p in base_peaks)
        spike_taller = (h4 - base_mean) / base_mean >= spike_min_excess_pct
        if not (peaks_similar and spike_taller):
            continue

        valley13_low = low.iloc[i1:i3 + 1].min()
        # Reject if first three peaks already confirmed as their own triple top
        # (price closed below valley13_low between i1 and i3).
        if close.iloc[i1:i3 + 1].min() < valley13_low:
            continue

        pattern_low = low.iloc[i1:i4 + 1].min()
        pattern_height = h4 - pattern_low
        if pattern_height <= 0:
            continue

        # Confirmation: first close after i4 that breaks below pattern_low.
        search_end = min(n, i4 + 1 + 40)
        for j in range(i4 + 1, search_end):
            if close.iloc[j] < pattern_low:
                short_trigger.iloc[j] = True
                stop_level.iloc[j] = h4
                target_level.iloc[j] = pattern_low - target_height_frac * pattern_height
                confirm_low_level.iloc[j] = pattern_low
                break
            if high.iloc[j] > h4:
                break  # invalidated by upward breakout per source's own rule

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
