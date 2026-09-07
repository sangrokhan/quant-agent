"""Strategy: Inverse Head and Shoulders (bullish reversal) neckline breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-1xx):
Per SERP-sourced rules (IG.com, Vantage Markets, naga.com snippets via
Google): an Inverse Head and Shoulders is a 3-trough reversal pattern --
left shoulder (swing low), head (a LOWER swing low than both shoulders),
right shoulder (a swing low roughly similar in depth to the left shoulder)
-- with a "neckline" drawn through the two intermediate swing highs between
the troughs. Entry is a long position on a decisive close above the
neckline; stop-loss placed below the right shoulder (or below the head, per
source); profit target uses the "measured move" technique: the vertical
distance from the head's low to the neckline, projected upward from the
breakout point. First Head & Shoulders variant tested in this repo --
distinct from the previously-tested/rejected Double Bottom (2026-09-08-101,
a 2-trough W-pattern) which this 3-trough pattern generalizes.

Signal logic
------------
- Identify swing pivots via the same rolling-window fractal test used in
  2026-09-08-107/108 (AB=CD/Gartley) to get alternating swing highs/lows.
- For each valid Low(shoulder1)-High(neckline1)-Low(head)-High(neckline2)-
  Low(shoulder2) quintuple where:
    head < shoulder1 and head < shoulder2 (head is the deepest trough)
    abs(shoulder1 - shoulder2) / head <= shoulder_symmetry_tolerance
      (shoulders roughly symmetric in depth, default 15%)
  the neckline level is approximated as the average of the two intermediate
  swing highs (neckline1, neckline2).
- Entry (long): first bar after shoulder2 where close breaks decisively
  above the neckline level (close > neckline * (1 + breakout_buffer)).
- Exit: close falls back below the right shoulder's low (stop-loss), OR
  close reaches the measured-move target (breakout_price + (neckline -
  head) * target_multiple), OR a max_hold_days time-stop.
- Flat otherwise.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _find_pivots(series: pd.Series, window: int) -> pd.Series:
    n = len(series)
    pivots = pd.Series(0, index=series.index, dtype=int)
    half = window // 2
    vals = series.values
    for i in range(half, n - half):
        window_vals = vals[i - half : i + half + 1]
        if vals[i] == window_vals.max() and (window_vals == vals[i]).sum() == 1:
            pivots.iloc[i] = 1
        elif vals[i] == window_vals.min() and (window_vals == vals[i]).sum() == 1:
            pivots.iloc[i] = -1
    return pivots


def generate_signals(
    price_df: pd.DataFrame,
    pivot_window: int = 11,
    shoulder_symmetry_tolerance: float = 0.15,
    breakout_buffer: float = 0.005,
    target_multiple: float = 1.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series for inverse H&S completions."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    high_pivots = _find_pivots(high, pivot_window)
    low_pivots = _find_pivots(low, pivot_window)

    swing_idx = []
    for i in range(len(df)):
        if high_pivots.iloc[i] == 1:
            swing_idx.append((i, "H", float(high.iloc[i])))
        if low_pivots.iloc[i] == -1:
            swing_idx.append((i, "L", float(low.iloc[i])))
    swing_idx.sort(key=lambda x: x[0])

    alt_swings = []
    for s in swing_idx:
        if alt_swings and alt_swings[-1][1] == s[1]:
            if s[1] == "H" and s[2] > alt_swings[-1][2]:
                alt_swings[-1] = s
            elif s[1] == "L" and s[2] < alt_swings[-1][2]:
                alt_swings[-1] = s
        else:
            alt_swings.append(s)

    patterns = []  # dicts with s2_idx (right shoulder swing index), neckline, head, shoulder2_low
    for k in range(len(alt_swings) - 4):
        s1, n1, h, n2, s2 = (
            alt_swings[k], alt_swings[k + 1], alt_swings[k + 2],
            alt_swings[k + 3], alt_swings[k + 4],
        )
        if not (s1[1] == "L" and n1[1] == "H" and h[1] == "L" and n2[1] == "H" and s2[1] == "L"):
            continue
        shoulder1, neckline1, head, neckline2, shoulder2 = s1[2], n1[2], h[2], n2[2], s2[2]
        if not (head < shoulder1 and head < shoulder2):
            continue
        if head <= 0:
            continue
        symmetry = abs(shoulder1 - shoulder2) / abs(head)
        if symmetry > shoulder_symmetry_tolerance:
            continue
        neckline = (neckline1 + neckline2) / 2.0
        patterns.append({"s2_idx": s2[0], "neckline": neckline, "head": head, "shoulder2_low": shoulder2})

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_price = 0.0
    target_price = 0.0
    used = set()

    c_arr = close.values
    n = len(c_arr)

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if c_arr[i] < stop_price or c_arr[i] >= target_price or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            for p_idx, p in enumerate(patterns):
                if p_idx in used:
                    continue
                if i <= p["s2_idx"]:
                    continue
                neckline = p["neckline"]
                if c_arr[i] > neckline * (1 + breakout_buffer):
                    in_position = True
                    entry_idx = i
                    stop_price = p["shoulder2_low"]
                    measured_move = neckline - p["head"]
                    target_price = c_arr[i] + measured_move * target_multiple
                    used.add(p_idx)
                    position.iloc[i] = 1
                    break
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
