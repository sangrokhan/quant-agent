"""Strategy: Descending Triangle BULLISH (upward) breakout, long-only.

Hypothesis (this iteration):
Per Bulkowski's own documented finding (via ChartScout.io SERP snippet:
"Thomas Bulkowski studied over 1,300 descending triangles and found they
actually break upward more often than downward"), a Descending Triangle
-- flat horizontal support (repeated tests of roughly the same low) with
a declining upper trendline (lower highs, OLS-fit negative slope)
converging toward that support -- is conventionally taught as a bearish
continuation pattern, but Bulkowski's own large-sample statistics
document the COUNTER-INTUITIVE finding that upward breakouts are both
MORE COMMON and produce a larger average gain than the conventionally-
expected downward breaks. This strategy trades that specific
counter-intuitive edge: long entry when price breaks UPWARD out of a
confirmed descending triangle (above the declining upper trendline),
rather than the conventional bearish-continuation trade.

Distinct from the already-tested Symmetrical Triangle (2026-09-08-102,
BOTH trendlines converge, one rising one falling) and Ascending Triangle
(2026-09-08-112, flat upper resistance + rising lower support -- the
mirror-image structure) since Descending Triangle has a FLAT LOWER
support + DECLINING upper resistance, and this strategy specifically
targets the anti-consensus upward-breakout direction per Bulkowski's own
disclosed statistics, not the naively-expected downward continuation.

Signal logic
------------
- Flat support: rolling min of low over pattern_window bars changes by
  less than support_flatness_pct across the window (a genuinely flat
  floor, not a sloped one).
- Declining resistance: OLS-fit slope of the rolling max of high over
  pattern_window bars is negative and its magnitude exceeds
  min_decline_pct (a genuine narrowing/declining upper boundary, not
  noise).
- Convergence: the triangle's range (declining-resistance value minus
  flat-support value) at the END of the window is narrower than at the
  START by at least convergence_ratio (confirms the two lines are
  actually converging, not just two unrelated trends).
- Entry (long): close breaks above the current (most-recently-projected)
  declining-resistance trendline value.
- Exit: close crosses back below the flat support level (pattern
  invalidated), a measured-move target (entry_price +
  reward_mult*(pattern's max range)), or a max_hold_days time-stop.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)

Sources:
    https://chartscout.io (Bulkowski statistic, via Google SERP snippet;
    direct page fetch 404'd this session)
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
    pattern_window: int = 30,
    support_flatness_pct: float = 0.03,
    min_decline_pct: float = 0.05,
    convergence_ratio: float = 0.4,
    reward_mult: float = 1.0,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    close = df["close"]
    n = len(close)
    c = close.to_numpy(dtype=float)
    h = high.to_numpy(dtype=float)
    l = low.to_numpy(dtype=float)

    x = np.arange(pattern_window, dtype=float)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()

    pattern_valid = np.zeros(n, dtype=bool)
    support_level = np.full(n, np.nan)
    resistance_at = np.full(n, np.nan)  # resistance value projected to bar i
    resistance_start = np.full(n, np.nan)  # resistance value at window start

    for i in range(pattern_window, n):
        window_low = l[i - pattern_window:i]
        window_high = h[i - pattern_window:i]

        support = window_low.min()
        support_range_pct = (window_low.max() - window_low.min()) / support if support != 0 else np.inf
        if support_range_pct > support_flatness_pct:
            continue

        y = window_high
        y_mean = y.mean()
        cov = ((x - x_mean) * (y - y_mean)).sum()
        slope = cov / x_var if x_var != 0 else 0.0
        intercept = y_mean - slope * x_mean

        res_start = intercept  # x=0
        res_end = intercept + slope * (pattern_window - 1)  # x=pattern_window-1 (last bar of window, i-1)

        if res_start == 0:
            continue
        decline_pct = (res_start - res_end) / res_start
        if decline_pct < min_decline_pct:
            continue

        range_start = res_start - support
        range_end = res_end - support
        if range_start <= 0:
            continue
        if (range_start - range_end) / range_start < convergence_ratio:
            continue

        pattern_valid[i] = True
        support_level[i] = support
        resistance_start[i] = res_start
        # project resistance forward to bar i (one step beyond res_end)
        resistance_at[i] = res_end + slope

    entry_cond = np.zeros(n, dtype=bool)
    support_at_entry = np.full(n, np.nan)
    target_at_entry = np.full(n, np.nan)

    for i in range(1, n):
        if pattern_valid[i] and c[i] > resistance_at[i]:
            entry_cond[i] = True
            support_at_entry[i] = support_level[i]
            pattern_range = resistance_start[i] - support_level[i]
            target_at_entry[i] = c[i] + reward_mult * pattern_range

    position = np.zeros(n, dtype=int)
    in_position = False
    entry_idx = 0
    stop_price = 0.0
    target_price = 0.0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            px = c[i]
            hit_stop = px < stop_price
            hit_target = px >= target_price
            hit_time = held >= max_hold_days
            if hit_stop or hit_target or hit_time:
                in_position = False
                position[i] = 0
                continue
            position[i] = 1
        else:
            if entry_cond[i]:
                in_position = True
                entry_idx = i
                stop_price = support_at_entry[i]
                target_price = target_at_entry[i]
                position[i] = 1
            else:
                position[i] = 0

    return pd.Series(position, index=close.index, dtype=int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
