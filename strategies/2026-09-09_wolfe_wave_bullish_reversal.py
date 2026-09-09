"""Strategy: Bullish Wolfe Wave 5-swing reversal pattern.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-048):
Per Investopedia's Wolfe Wave guide (visited this iteration,
https://www.investopedia.com/terms/w/wolfewave.asp) and Dhan.co's more
operational writeup (visited this iteration,
https://dhan.co/blog/technical-analysis/wolfe-wave-pattern/): a bullish
Wolfe Wave is a 5-swing-point reversal pattern that forms during a
downtrend. Points 1,3,5 are swing LOWS and points 2,4 are swing HIGHS.
Waves 3 and 4 must stay roughly within the channel drawn from waves 1-2.
Wave 5 makes a LOWER LOW than wave 3, typically overshooting the 1-3
trendline slightly, before price reverses higher. The projected target
("Estimated Price at Arrival", EPA) is the line connecting wave 1 and
wave 4, extended forward. Dhan.co's own summary: "Traders usually enter
after confirmation that buyers are gaining control" and "the projected
target is typically calculated by connecting Waves 1 and 4 and extending
the line forward."

This is a first Wolfe-Wave-pattern strategy in this repo (no prior
Wolfe/Elliott-wave-family entries found in strategies_index.jsonl),
distinct from all existing candlestick/single-pivot reversal strategies
because it requires a full 5-point alternating swing structure with a
channel/overshoot geometric constraint, not a 1-3 bar price/candle
pattern.

Signal logic (daily-bar approximation)
---------------------------------------
- Detect swing pivots via scipy.signal.argrelextrema with a symmetric
  window (`pivot_window`) on close price: local minima = swing lows,
  local maxima = swing highs.
- Scan the alternating pivot sequence for a 5-point low-high-low-high-low
  (L1,H2,L3,H4,L5) pattern where:
    * L3 < L1 (wave 3 extends beyond wave 1, per Dhan's "Wave 3: Price
      extends beyond Wave 1 while remaining within the developing
      channel")
    * L5 < L3 (wave 5 makes a lower low, the defining overshoot feature)
    * H4 < H2 (upper trendline 2-4 is also descending, forming a
      converging/parallel channel consistent with "wedge structure")
- Entry (long): on the first bar AFTER pivot L5 where close rises back
  above the local high formed since L5 (confirmation the reversal is
  underway, per Dhan's "wait for confirmation that buyers are gaining
  control" -- operationalized here as close > SMA(confirm_window)
  computed over the bars since L5).
- Target (EPA): the line from wave1 through wave4 extrapolated forward
  in time to the entry bar -- if price reaches/exceeds this target,
  exit (take profit).
- Stop: close falls below wave 5's low (pattern invalidated).
- Time-stop: max_hold_days if neither target nor stop is hit.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _find_pivots(close: pd.Series, pivot_window: int) -> pd.DataFrame:
    """Return a DataFrame of pivot points: index positions, price, and kind
    ('L' for swing low, 'H' for swing high), in chronological order.
    """
    from scipy.signal import argrelextrema

    vals = close.values
    n = len(vals)
    if n < (2 * pivot_window + 1):
        return pd.DataFrame(columns=["pos", "price", "kind"])

    lo_idx = argrelextrema(vals, np.less_equal, order=pivot_window)[0]
    hi_idx = argrelextrema(vals, np.greater_equal, order=pivot_window)[0]

    pivots = []
    for i in lo_idx:
        pivots.append((int(i), float(vals[i]), "L"))
    for i in hi_idx:
        pivots.append((int(i), float(vals[i]), "H"))
    pivots.sort(key=lambda x: x[0])

    # Collapse consecutive same-kind pivots (keep the most extreme one).
    cleaned = []
    for p in pivots:
        if cleaned and cleaned[-1][2] == p[2]:
            if p[2] == "L" and p[1] < cleaned[-1][1]:
                cleaned[-1] = p
            elif p[2] == "H" and p[1] > cleaned[-1][1]:
                cleaned[-1] = p
            # else keep existing
        else:
            cleaned.append(p)

    return pd.DataFrame(cleaned, columns=["pos", "price", "kind"])


def _find_bullish_wolfe_waves(pivots: pd.DataFrame) -> list[dict]:
    """Scan the alternating pivot sequence for bullish Wolfe Wave
    (L1, H2, L3, H4, L5) 5-tuples satisfying the channel/overshoot rules.
    """
    patterns = []
    kinds = pivots["kind"].tolist()
    n = len(pivots)
    for i in range(n - 4):
        window = pivots.iloc[i : i + 5]
        wk = window["kind"].tolist()
        if wk != ["L", "H", "L", "H", "L"]:
            continue
        L1, H2, L3, H4, L5 = window.itertuples(index=False)
        if not (L3.price < L1.price):
            continue
        if not (L5.price < L3.price):
            continue
        if not (H4.price < H2.price):
            continue
        patterns.append(
            {
                "L1": L1, "H2": H2, "L3": L3, "H4": H4, "L5": L5,
            }
        )
    return patterns


def generate_signals(
    price_df: pd.DataFrame,
    pivot_window: int = 5,
    confirm_window: int = 3,
    max_hold_days: int = 20,
    target_multiplier: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    if n < (2 * pivot_window + 10):
        return position

    pivots = _find_pivots(close, pivot_window)
    if len(pivots) < 5:
        return position

    patterns = _find_bullish_wolfe_waves(pivots)
    if not patterns:
        return position

    close_vals = close.values
    used_until = -1  # avoid overlapping trades

    for pat in patterns:
        l5_pos = pat["L5"].pos
        if l5_pos <= used_until:
            continue
        l1_pos, l1_price = pat["L1"].pos, pat["L1"].price
        h4_pos, h4_price = pat["H4"].pos, pat["H4"].price

        # EPA target line: connects (l1_pos, l1_price) -> (h4_pos, h4_price),
        # extrapolated forward in time.
        if h4_pos == l1_pos:
            continue
        slope = (h4_price - l1_price) / (h4_pos - l1_pos)

        # Confirmation window: look for close crossing back above the
        # rolling max since L5 within the next `pivot_window` bars after L5.
        search_start = l5_pos + 1
        search_end = min(n, l5_pos + 1 + pivot_window + confirm_window)
        entry_pos = None
        local_high_since_l5 = close_vals[l5_pos]
        for j in range(search_start, search_end):
            local_high_since_l5 = max(local_high_since_l5, close_vals[j])
            if j >= search_start + confirm_window - 1:
                recent = close_vals[max(search_start, j - confirm_window + 1) : j + 1]
                if close_vals[j] > recent.mean() and close_vals[j] > pat["L5"].price:
                    entry_pos = j
                    break
        if entry_pos is None:
            continue

        stop_price = pat["L5"].price
        exit_pos = None
        for k in range(entry_pos, min(n, entry_pos + max_hold_days)):
            target_price = l1_price + slope * (k - l1_pos) * target_multiplier
            if close_vals[k] < stop_price:
                exit_pos = k
                break
            if close_vals[k] >= target_price and k > entry_pos:
                exit_pos = k
                break
        if exit_pos is None:
            exit_pos = min(n - 1, entry_pos + max_hold_days - 1)

        position.iloc[entry_pos : exit_pos + 1] = 1
        used_until = exit_pos

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
