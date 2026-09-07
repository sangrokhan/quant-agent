"""Strategy: Double Bottom (W-pattern) neckline breakout, long-only.

Hypothesis (knowledge_base id=2026-09-08-101): Per Investopedia's Double
Bottom explainer (https://www.investopedia.com/terms/d/doublebottom.asp):
a "double bottom" reversal forms when price makes a swing low, rebounds to
an intermediate high (the "neckline"), pulls back to a second low within a
few percent of the first low, then a daily close above the intermediate
high ("neckline breakout") signals a valid reversal worth a long entry.
Source's own stated rule: "A long position is recommended on a daily close
above the first rebound's high, with a stop loss at the pattern's second
low." First chart-pattern strategy in this repo built specifically around
a two-trough W-shape with an explicit similarity tolerance between the two
lows (distinct from the already-tested single-swing Turtle Soup fade
(2026-09-04-076) and generic Donchian/Turtle breakouts, none of which
require a *second* low near the first).

Signal logic
------------
- Identify local swing lows via a rolling-window argmin (pivot_window bars
  each side must not be lower).
- Low #1: a confirmed swing low. Neckline: the highest close between low #1
  and a subsequent second swing low. Low #2: a later confirmed swing low
  occurring within max_pattern_bars of low #1, whose price is within
  low_similarity_pct of low #1 (source: "second low of the pattern is
  within 3% to 4% of the prior low").
- Entry (long): first daily close, after low #2 has formed, that closes
  above the neckline high (source's "daily close above the intermediate
  high").
- Exit: close falls back below low #2's price (source's stop-at-second-low
  rule), OR close reaches the minimum measured target (neckline +
  (neckline - low #2), the source's "distance between the lows and the
  intermediate high" projected up from the breakout), OR a max_hold_days
  time-stop backstop (source gives no explicit time limit).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _swing_lows(low: pd.Series, pivot_window: int) -> pd.Series:
    """Boolean series: True where `low` is a confirmed local minimum over
    a +/- pivot_window bar window (confirmed pivot_window bars after the
    fact, since we need the right-side bars too -- no look-ahead in the
    entry logic since we only USE a confirmed pivot after it is confirmed).
    """
    n = len(low)
    is_low = pd.Series(False, index=low.index)
    vals = low.values
    for i in range(pivot_window, n - pivot_window):
        window = vals[i - pivot_window: i + pivot_window + 1]
        if vals[i] == window.min():
            is_low.iloc[i] = True
    return is_low


def generate_signals(
    price_df: pd.DataFrame,
    pivot_window: int = 5,
    low_similarity_pct: float = 0.04,
    max_pattern_bars: int = 60,
    min_pattern_bars: int = 10,
    target_mult: float = 1.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]
    n = len(df)

    is_swing_low = _swing_lows(low, pivot_window)
    swing_low_idx = [i for i in range(n) if bool(is_swing_low.iloc[i])]

    position = pd.Series(0, index=close.index, dtype=int)

    in_position = False
    entry_idx = 0
    stop_price = None
    target_price = None

    # For each bar, track the most recent *confirmed* double-bottom pattern
    # (low1, low2, neckline_high, neckline_idx) that hasn't yet triggered
    # entry, so we can watch for the breakout close on a later bar.
    pending = None  # (low1_val, low2_val, low2_idx, neckline_val)

    swing_ptr = 0  # pointer into swing_low_idx for lows confirmed so far

    for i in range(n):
        # Confirm any newly-available swing lows (a swing low at index j is
        # only "known" once bar j+pivot_window has passed, per _swing_lows'
        # construction -- but since is_swing_low was already computed with
        # no look-ahead beyond j+pivot_window, we just need i >= j+pivot_window).
        while swing_ptr < len(swing_low_idx) and swing_low_idx[swing_ptr] + pivot_window <= i:
            j = swing_low_idx[swing_ptr]
            swing_ptr += 1
            # Try to pair this new low (j) as a "low #2" against a recent
            # prior low (candidate low #1) within max_pattern_bars.
            for k in range(swing_ptr - 2, -1, -1):
                j1 = swing_low_idx[k]
                if j - j1 > max_pattern_bars:
                    break
                if j - j1 < min_pattern_bars:
                    continue
                low1_val = low.iloc[j1]
                low2_val = low.iloc[j]
                if low1_val <= 0:
                    continue
                if abs(low2_val - low1_val) / low1_val > low_similarity_pct:
                    continue
                # neckline = highest close between j1 and j
                between = close.iloc[j1:j + 1]
                if len(between) < 2:
                    continue
                neckline_val = between.max()
                pending = (low1_val, low2_val, j, neckline_val)
                break  # take the most recent valid low1 pairing

        if in_position:
            held = i - entry_idx
            c = close.iloc[i]
            if (c <= stop_price) or (c >= target_price) or (held >= max_hold_days):
                in_position = False
                position.iloc[i] = 0
                pending = None
                continue
            position.iloc[i] = 1
            continue

        # Not in position: check breakout trigger against pending pattern.
        if pending is not None:
            low1_val, low2_val, j2, neckline_val = pending
            c = close.iloc[i]
            if i > j2 and c > neckline_val:
                in_position = True
                entry_idx = i
                stop_price = low2_val
                measured_move = (neckline_val - low2_val) * target_mult
                target_price = neckline_val + measured_move
                position.iloc[i] = 1
                pending = None
                continue
        position.iloc[i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
