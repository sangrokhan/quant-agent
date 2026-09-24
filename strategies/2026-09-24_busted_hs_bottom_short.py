"""Strategy: Busted Head-and-Shoulders Bottom (bearish continuation SHORT).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from https://thepatternsite.com/BustHSB.html (Thomas Bulkowski,
browser_exec fallback -- web_search's DDGS backend has no `extract`
capability for this domain and returned no usable snippet content for the
"triple bottom" companion query this iteration). Source's own disclosed
rules and statistics:

    "A stock forms a head-and-shoulders bottom which confirms as a valid
    pattern when price closes above the neckline or right armpit... Price
    rises no more than 10% before dropping and closing below the bottom of
    the chart pattern. This busts the upward breakout... For busted
    patterns in bull markets, the average drop is 13[%]. If you trade a
    single busted head-and-shoulders bottom, the average decline is 22%...
    16% of head-and-shoulders bottoms will bust. Of those that bust...47%
    will single bust."

This is a distinct hypothesis from this repo's existing
2026-09-08_inverse_head_shoulders_neckline.py (which trades the confirmed
breakout LONG). This strategy instead trades the FAILURE mode: it reuses
the same inverse-H&S pattern/neckline detection, but only enters (SHORT)
when the source's own "bust" condition triggers -- price confirms the
breakout, rises less than `bust_rise_cap` above the neckline, then closes
back below the pattern's bottom (the head's low). That is a genuinely
different signal-generation mechanism (post-breakout failure detection,
not the breakout itself) operationalizing a numeric rule (source's own
"10%" rise cap) not previously coded in this repo.

Signal logic
------------
1. Reuse alternating-swing pivot detection (same fractal test as
   2026-09-08's inverse H&S file) to find Low(shoulder1)-High(neckline1)-
   Low(head)-High(neckline2)-Low(shoulder2) quintuples with head the
   deepest trough and shoulders roughly symmetric
   (`shoulder_symmetry_tolerance`).
2. Confirmation: first close after shoulder2 that closes above the
   neckline (average of neckline1/neckline2) -- this is the "valid
   pattern" breakout point per source.
3. Bust check: from the confirmation bar onward, track the running max
   close. If that running max close exceeds neckline * (1 + bust_rise_cap)
   BEFORE any bust, the pattern is disqualified (didn't bust within the
   source's 10% ceiling) -- no trade.
4. Entry (SHORT): the first bar, while still within the bust_rise_cap
   ceiling, where close drops back below the pattern's bottom (the head's
   low price) -- this is the source's own "closes below the bottom of the
   chart pattern" bust trigger.
5. Exit: source's own average single-bust decline is 22% -- target_pct
   default 0.22 measured from the bust-entry close (price falls further,
   short profits), OR close recovers back above the top of the pattern
   (shoulder/neckline high, stop-loss on the short), OR a max_hold_days
   time-stop, whichever comes first.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({-1,0} position series;
        -1 = short, 0 = flat -- generate_returns handles the sign so a
        short position produces a positive return when price falls)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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


def _find_inverse_hs_patterns(df: pd.DataFrame, pivot_window: int, shoulder_symmetry_tolerance: float):
    high, low = df["high"], df["low"]
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

    patterns = []
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
        pattern_top = max(shoulder1, neckline1, neckline2, shoulder2)
        patterns.append({
            "s2_idx": s2[0], "neckline": neckline, "head": head,
            "pattern_bottom": head,  # bottom of the chart pattern = the head's low
            "pattern_top": pattern_top,
        })
    return patterns


def generate_signals(
    price_df: pd.DataFrame,
    pivot_window: int = 11,
    shoulder_symmetry_tolerance: float = 0.15,
    breakout_buffer: float = 0.005,
    bust_rise_cap: float = 0.10,
    target_pct: float = 0.22,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {-1,0} short/flat position series for busted inverse-H&S bottoms."""
    df = _prep(price_df)
    close = df["close"]
    c_arr = close.values
    n = len(c_arr)

    patterns = _find_inverse_hs_patterns(df, pivot_window, shoulder_symmetry_tolerance)

    # Track per-pattern state: confirmed (breakout happened), running max
    # close since confirmation, busted (entered short).
    pat_state = []
    for p in patterns:
        pat_state.append({
            **p,
            "confirmed": False,
            "confirm_idx": None,
            "running_max": None,
            "disqualified": False,
            "used": False,
        })

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_price = 0.0
    stop_price = 0.0
    target_price = 0.0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            recovered = c_arr[i] > stop_price
            hit_target = c_arr[i] <= target_price
            if recovered or hit_target or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = -1
            continue

        # Update pattern states and look for a fresh bust-entry this bar.
        entered_this_bar = False
        for p in pat_state:
            if p["used"] or p["disqualified"]:
                continue
            if i <= p["s2_idx"]:
                continue
            neckline = p["neckline"]
            ceiling = neckline * (1 + bust_rise_cap)

            if not p["confirmed"]:
                if c_arr[i] > neckline * (1 + breakout_buffer):
                    p["confirmed"] = True
                    p["confirm_idx"] = i
                    p["running_max"] = c_arr[i]
                continue

            # confirmed: track running max, check disqualification/bust
            p["running_max"] = max(p["running_max"], c_arr[i])
            if p["running_max"] > ceiling:
                p["disqualified"] = True
                continue
            if not entered_this_bar and c_arr[i] < p["pattern_bottom"]:
                # Bust trigger: short entry
                in_position = True
                entered_this_bar = True
                entry_idx = i
                entry_price = c_arr[i]
                stop_price = p["pattern_top"]
                target_price = entry_price * (1 - target_pct)
                p["used"] = True
                position.iloc[i] = -1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs).

    Position is -1 while short; multiplying by daily returns means a
    price DROP while short (position=-1) produces a POSITIVE strategy
    return, matching a real short position's payoff.
    """
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
