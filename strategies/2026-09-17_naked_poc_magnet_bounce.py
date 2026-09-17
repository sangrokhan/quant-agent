"""Strategy: Naked (untested) weekly Point-of-Control magnet bounce.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-176):
Per LuxAlgo's "Naked POC" concept (https://www.luxalgo.com/library, read via
browser_exec Google SERP snippets this iteration -- direct concept page
404'd, formula confirmed from LuxAlgo's own disclosed definition repeated
across their "Point of Control" and "Naked POC" pages): "A naked POC (also
called a virgin POC, or NPOC) is a prior session's point of control that
price has not traded back through since that session ended." Because a
naked POC marks a price level where a large concentration of prior volume
transacted but which the market has since moved away from without
revisiting, it is treated by many practitioners as a "magnet" -- unfinished
business the market statistically tends to eventually trade back through.
This is distinct from every prior Volume-Profile strategy in this repo
(2026-09-04-150 VAL mean-reversion, 2026-09-08-129 VAH breakout,
2026-09-10-001 VAL retest, 2026-09-16-183 80% Rule Value Area re-entry),
all of which use a CONTINUOUSLY ROLLING N-day profile recomputed every bar.
This strategy instead uses DISCRETE WEEKLY profiles (one POC per completed
calendar week) and explicitly tracks which of those POCs remain "naked"
(never subsequently touched) -- a session/period-based construction, not a
rolling-window one, matching LuxAlgo's own definition of the concept.

Signal logic
------------
- Group daily bars into ISO calendar weeks. For each COMPLETED week, build
  a coarse volume profile: bin that week's HLC3 into n_bins price buckets,
  weight each day's contribution by its volume, and set that week's POC to
  the CENTER of the highest-weighted bin.
- A week's POC becomes "naked" as soon as the week ends. It stays naked
  until some later day's [low, high] range trades through it (an intraday
  or intra-bar touch counts as a fill, matching the concept's own
  "price... has not traded back through" definition) -- after which it is
  removed from the naked set permanently.
- Entry (long): today's close is within magnet_tolerance_pct ABOVE a
  currently-naked POC that lies below today's close (price has pulled back
  down toward an untested magnet from above -- the "unfinished business"
  is nearby), AND close > SMA(trend_window) (only trade magnet-bounces
  with the broader trend, per this repo's established trend-gate pattern).
- Exit: close rises profit_target_pct above the entry-triggering POC level
  (bounce played out), OR that POC gets filled/touched (thesis resolved,
  whether or not profit target hit), OR a max_hold_days time-stop.
- Flat otherwise; long-only, single position at a time. Only the most
  recent max_naked_lookback_weeks of naked POCs are considered (avoid an
  unbounded growing candidate set).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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


def _weekly_poc_series(df: pd.DataFrame, n_bins: int) -> dict:
    """Compute one POC per completed ISO week, keyed by the week's end date
    (last bar's timestamp within that week)."""
    hlc3 = (df["high"] + df["low"] + df["close"]) / 3.0
    week_key = df.index.to_series().dt.isocalendar().apply(lambda r: (r["year"], r["week"]), axis=1)
    pocs = {}
    for key, idx in df.groupby(week_key).groups.items():
        week_df = df.loc[idx]
        if len(week_df) < 2:
            continue
        wk_hlc3 = hlc3.loc[idx]
        lo, hi = wk_hlc3.min(), wk_hlc3.max()
        if hi <= lo:
            poc_level = wk_hlc3.iloc[-1]
        else:
            bins = np.linspace(lo, hi, n_bins + 1)
            bin_idx = np.clip(np.digitize(wk_hlc3.values, bins) - 1, 0, n_bins - 1)
            weights = np.zeros(n_bins)
            for b, vol in zip(bin_idx, week_df["volume"].values):
                weights[b] += vol
            best_bin = int(np.argmax(weights))
            poc_level = (bins[best_bin] + bins[best_bin + 1]) / 2.0
        week_end = week_df.index[-1]
        pocs[week_end] = float(poc_level)
    return pocs


def generate_signals(
    price_df: pd.DataFrame,
    n_bins: int = 10,
    magnet_tolerance_pct: float = 0.01,
    profit_target_pct: float = 0.02,
    trend_window: int = 100,
    max_hold_days: int = 15,
    max_naked_lookback_weeks: int = 8,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]
    high = df["high"]
    n = len(close)

    trend_sma = close.rolling(trend_window, min_periods=trend_window).mean()

    weekly_pocs = _weekly_poc_series(df, n_bins)
    # Sort naked-POC candidates chronologically by week-end date.
    poc_events = sorted(weekly_pocs.items(), key=lambda kv: kv[0])

    position = pd.Series(0, index=close.index, dtype=int)
    naked = []  # list of poc levels currently untested, in creation order
    poc_ptr = 0

    in_position = False
    hold_days = 0
    entry_poc = None

    idx_list = df.index

    for i in range(n):
        today = idx_list[i]
        px_close = close.iloc[i]
        px_low = low.iloc[i]
        px_high = high.iloc[i]
        sma = trend_sma.iloc[i]

        # Activate any POCs whose week ended on or before today.
        while poc_ptr < len(poc_events) and poc_events[poc_ptr][0] <= today:
            naked.append(poc_events[poc_ptr][1])
            poc_ptr += 1
        if len(naked) > max_naked_lookback_weeks:
            naked = naked[-max_naked_lookback_weeks:]

        # Remove any naked POCs this bar's range trades through (filled).
        still_naked = []
        filled_this_bar = set()
        for level in naked:
            if px_low <= level <= px_high:
                filled_this_bar.add(level)
            else:
                still_naked.append(level)
        naked = still_naked

        if in_position:
            hold_days += 1
            target_hit = px_close >= entry_poc * (1 + profit_target_pct)
            thesis_resolved = entry_poc in filled_this_bar
            if target_hit or thesis_resolved or hold_days >= max_hold_days:
                in_position = False
                entry_poc = None
                hold_days = 0
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
            continue

        # Look for an entry: nearest naked POC below today's close, within
        # tolerance.
        if sma == sma and px_close > sma and naked:
            below = [lvl for lvl in naked if lvl < px_close]
            if below:
                nearest = max(below)  # closest one below close
                if (px_close - nearest) / nearest <= magnet_tolerance_pct:
                    in_position = True
                    entry_poc = nearest
                    hold_days = 0
                    position.iloc[i] = 1
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
