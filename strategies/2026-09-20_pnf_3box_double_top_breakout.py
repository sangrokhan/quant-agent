"""Strategy: Point & Figure (P&F) 3-box-reversal Double Top Breakout / Double
Bottom Breakdown trend-follower.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per stockcharts.com ChartSchool's "P&F Price Objectives: Breakout and
Reversal Method" page (chartschool.stockcharts.com) and tradealgo.com's P&F
explainer (both visited this iteration): a classic Point & Figure chart
converts a close-price series into columns of X's (rising) and O's
(falling), only starting a new column when price reverses by a fixed
"reversal amount" (standard: 3 boxes, i.e. 3x the box size) from the last
extreme. The most basic, "most prolific" P&F trading signal per
stockcharts.com is the Double Top Breakout (go long when the current
X-column's high exceeds the immediately preceding X-column's high) and its
mirror-image Double Bottom Breakdown (go flat/short when the current
O-column's low breaches the immediately preceding O-column's low). This is
a genuinely distinct construction from every other strategy in this repo:
it filters out sub-reversal-threshold noise entirely by only updating state
on a 3-box move (unlike Renko, which uses a FIXED brick size with no
reversal-amount rule, or Donchian/rolling-high breakouts, which look at the
raw daily high/low series with no noise-filtering column construction).

Operationalized here as a long/flat overlay: hold long from the bar where a
Double Top Breakout fires until either the opposite Double Bottom Breakdown
fires (exit to flat) or a new one fires again (stay long). `box_size_pct`
sets the box size as a percentage of price (percentage/ATR-style scaling,
since fixed-point traditional scaling doesn't translate across
tickers/asset classes); `reversal_boxes` sets the reversal-amount
multiplier (standard 3, tested here plus 2 and 4 as a robustness check).

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _build_pnf_columns(close: pd.Series, box_size_pct: float, reversal_boxes: int):
    """Construct P&F columns from a close-price series using percentage box
    scaling. Returns two arrays aligned to `close.index`:
      - col_direction: +1 (X-column/rising) or -1 (O-column/falling) or 0
        (undefined, before the first column starts) for each bar.
      - col_extreme: the running extreme (high for X, low for O) of the
        CURRENT column as of that bar (this is what "exceeds the prior
        column's extreme" compares against for the breakout/breakdown
        signal at the point a NEW column starts).
    Also returns a boolean array `new_col_start` marking bars where a brand
    new column begins (reversal triggered), and the extreme of the PRIOR
    completed column of the same type two-back (needed for the double
    top/bottom comparison) via `prior_same_type_extreme`.
    """
    n = len(close)
    vals = close.values.astype(float)

    col_direction = np.zeros(n, dtype=int)
    col_extreme = np.full(n, np.nan)
    new_col_start = np.zeros(n, dtype=bool)
    # extreme of the most recently COMPLETED column of each type, updated
    # only when a column of that type closes out (a new opposite column
    # starts) -- this is the "prior X-column high" / "prior O-column low"
    # basic double top/bottom comparison target.
    last_completed_x_high = np.nan
    last_completed_o_low = np.nan
    prior_same_type_extreme = np.full(n, np.nan)

    direction = 0  # 0 = undefined, +1 = X (up), -1 = O (down)
    running_extreme = vals[0]

    for i in range(n):
        price = vals[i]
        if direction == 0:
            # Still establishing the first column: track both directions
            # until a reversal_boxes-sized move commits us to X or O.
            if price >= running_extreme * (1 + box_size_pct):
                direction = 1
                running_extreme = price
                new_col_start[i] = True
            elif price <= running_extreme * (1 - box_size_pct):
                direction = -1
                running_extreme = price
                new_col_start[i] = True
            else:
                running_extreme = max(running_extreme, price) if price > running_extreme else running_extreme
        elif direction == 1:
            if price > running_extreme:
                running_extreme = price
            elif price <= running_extreme * (1 - box_size_pct * reversal_boxes):
                # Reversal: current X-column completes.
                last_completed_x_high = running_extreme
                direction = -1
                running_extreme = price
                new_col_start[i] = True
        else:  # direction == -1
            if price < running_extreme:
                running_extreme = price
            elif price >= running_extreme * (1 + box_size_pct * reversal_boxes):
                last_completed_o_low = running_extreme
                direction = 1
                running_extreme = price
                new_col_start[i] = True

        col_direction[i] = direction
        col_extreme[i] = running_extreme
        prior_same_type_extreme[i] = last_completed_x_high if direction == 1 else last_completed_o_low

    return col_direction, col_extreme, new_col_start, prior_same_type_extreme


def generate_signals(
    price_df: pd.DataFrame,
    box_size_pct: float = 0.02,
    reversal_boxes: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry: a Double Top Breakout -- the CURRENT X-column's running high
    exceeds the most recently completed prior X-column's high.
    Exit to flat: a Double Bottom Breakdown -- the CURRENT O-column's
    running low breaches the most recently completed prior O-column's low.
    Stays in its last state otherwise (there is always exactly one "active"
    P&F signal, per stockcharts.com's own description).
    """
    df = _prep(price_df)
    close = df["close"]

    col_direction, col_extreme, _new_col_start, prior_same_type_extreme = _build_pnf_columns(
        close, box_size_pct=box_size_pct, reversal_boxes=reversal_boxes
    )

    is_x = col_direction == 1
    is_o = col_direction == -1

    double_top_breakout = is_x & (col_extreme > prior_same_type_extreme)
    double_bottom_breakdown = is_o & (col_extreme < prior_same_type_extreme)

    position = np.zeros(len(close), dtype=int)
    state = 0
    for i in range(len(close)):
        if double_top_breakout[i]:
            state = 1
        elif double_bottom_breakdown[i]:
            state = 0
        position[i] = state

    return pd.Series(position, index=close.index, dtype=int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
