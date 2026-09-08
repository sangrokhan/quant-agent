"""Strategy: Bump-and-Run Reversal (BARR) Bottom, long-only breakout.

Hypothesis (this iteration):
Per StockCharts ChartSchool (https://chartschool.stockcharts.com/table-of-contents/chart-analysis/chart-patterns/bump-and-run-reversal)
and multiple corroborating sources (RizeTrade, Warrior Trading, Taurex),
the Bump-and-Run Reversal (BARR) is a 3-phase pattern (Thomas Bulkowski's
own testing ranks it among the highest-performing of 39 chart patterns):

1. Lead-in phase: price declines in an orderly fashion along a trend
   line (in the BOTTOM variant tested here -- the long-entry analog of
   the source's more commonly illustrated TOP variant) for lead_in_window
   bars or more, at a moderate slope.
2. Bump phase: price accelerates AWAY from (below, for a bottom) the
   lead-in trend line's extrapolated projection by more than
   bump_threshold_pct -- a steeper, speculative/panic move distinct from
   the orderly lead-in.
3. Run phase: price breaks back ABOVE the lead-in trend line (source's
   own "exact entry rule": "the run phase begins when the pattern breaks
   [back across] the lead-in trend line... wait for the price to close
   completely" back across it) -- this is the long entry.

Exit: stop-loss placed "just beyond the extreme trough of the bump phase"
(source's own rule) OR a max_hold_days time-stop backstop, OR a
reward_mult*bump-depth profit target (approximating the source's
"measured move" price-objective convention without needing the full
formal calculation).

First Bump-and-Run Reversal pattern tested in this repo -- distinct from
every prior trend-line/breakout pattern (Rectangle 2026-09-08-111,
Darvas Box 2026-09-05-054, Cup-and-Handle 2026-09-06-172) via its
specific 3-phase lead-in/bump/run structure with a trend-line-extrapolation
deviation threshold defining the "bump" as distinct from the "lead-in".

Signal logic
------------
- lead_in_slope: rolling OLS slope of close vs. time over lead_in_window
  bars, computed lead_in_window bars BEFORE the current bar (i.e. the
  trend line is fit on the period preceding the potential bump).
- trend_line_projection: the lead-in OLS line's fitted value extrapolated
  forward to the current bar.
- bump_low: the lowest close reached after the lead-in period and before
  the current bar (within a bump_window lookback).
- Bump confirmed: bump_low is below trend_line_projection by more than
  bump_threshold_pct (i.e. price fell away from its own trend line by a
  meaningful amount -- the "panic" acceleration).
- Entry (long): close crosses back ABOVE the extrapolated lead-in trend
  line value at the current bar, having had a confirmed bump within the
  preceding bump_window bars.
- Exit: close crosses below the bump-phase low (stop, source's own
  placement rule) OR close reaches entry_price + reward_mult*(trend_line
  - bump_low) (measured-move-style profit target) OR a max_hold_days
  time-stop.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)

Sources:
    https://chartschool.stockcharts.com/table-of-contents/chart-analysis/chart-patterns/bump-and-run-reversal
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
    lead_in_window: int = 40,
    bump_window: int = 20,
    bump_threshold_pct: float = 0.08,
    reward_mult: float = 1.0,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)
    c = close.to_numpy(dtype=float)

    x = np.arange(lead_in_window, dtype=float)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()

    # trend_proj[i] = the lead-in OLS line (fit on bars
    # [i-lead_in_window-bump_window, i-bump_window)) extrapolated to bar i.
    trend_proj = np.full(n, np.nan)
    for i in range(lead_in_window + bump_window, n):
        lead_start = i - bump_window - lead_in_window
        lead_end = i - bump_window
        y = c[lead_start:lead_end]
        y_mean = y.mean()
        cov = ((x - x_mean) * (y - y_mean)).sum()
        slope = cov / x_var if x_var != 0 else 0.0
        intercept = y_mean - slope * x_mean
        # extrapolate to bar i, which is (lead_in_window + bump_window)
        # steps ahead of x=0 (the start of the lead-in window)
        steps_ahead = lead_in_window + bump_window
        trend_proj[i] = intercept + slope * steps_ahead

    bump_low = np.full(n, np.nan)
    for i in range(bump_window, n):
        bump_low[i] = np.min(c[i - bump_window:i]) if i - bump_window < i else np.nan

    bump_confirmed = np.zeros(n, dtype=bool)
    valid = ~np.isnan(trend_proj) & ~np.isnan(bump_low)
    bump_confirmed[valid] = (
        (trend_proj[valid] - bump_low[valid]) / np.where(trend_proj[valid] != 0, np.abs(trend_proj[valid]), np.nan)
        > bump_threshold_pct
    )

    entry_cond = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if np.isnan(trend_proj[i]) or np.isnan(trend_proj[i - 1]):
            continue
        crossed_up = (c[i] > trend_proj[i]) and (c[i - 1] <= trend_proj[i - 1])
        if crossed_up and bump_confirmed[i]:
            entry_cond[i] = True

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
                stop_price = bump_low[i] if not np.isnan(bump_low[i]) else 0.0
                measured_move = (trend_proj[i] - bump_low[i]) if not np.isnan(bump_low[i]) else 0.0
                target_price = c[i] + reward_mult * measured_move
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
