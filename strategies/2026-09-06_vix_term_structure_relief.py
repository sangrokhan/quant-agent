"""Strategy: VIX term-structure "buy the relief" (backwardation resolution).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-127):
Per Options Cafe's 17-year study of VIX/VIX3M term-structure episodes: the
onset of VIX backwardation (VIX crossing above VIX3M, ratio > 1.0) is NOT a
buy signal (the S&P kept falling 74% of the time after onset, roughly a
coin-flip at 5 days). The edge is at RESOLUTION -- when the ratio crosses
back below 1.0 (VIX3M > VIX again, i.e. term structure normalizes back to
contango) -- which the source's own backtest found positive 88-91% of the
time at +5/+21/+63 trading days, roughly 2-4x a random-day baseline. The
source explicitly gives a no-lookahead-safe version of the rule: use a
5-day rolling average of the VIX/VIX3M ratio to detect the crossing (raw
daily ratio is noisier / has some look-ahead ambiguity around exact
crossing days).

Operationalized on SPY (since VIX/VIX3M measure S&P 500 index options,
SPY is the natural equity proxy to trade the signal on, consistent with
this repo's other index-vol-driven QQQ/SPY strategies): compute a
`smooth_window`-day rolling average of VIX/VIX3M; flag "in backwardation"
when that smoothed ratio > `entry_ratio_threshold` (default 1.0); long
entry on SPY when the smoothed ratio crosses back below
`exit_ratio_threshold` (default 1.0) having previously been above it
(i.e. the resolution crossing) -- NOT on the onset itself, per the source's
finding that onset has no edge. Exit after a `hold_days` fixed holding
period (the source found the edge holds and even compounds out to ~63
trading days, so a fixed-hold time-based exit is a faithful reproduction of
the source's own "buy the relief, hold 1-3 months" playbook) OR immediately
if the ratio flips back into backwardation above `entry_ratio_threshold`
again (fresh onset -- de-risk per the source's playbook).

Source: https://options.cafe/blog/vix-term-structure-contango-backwardation/
(read via browser_exec; web_search errored for this iteration's query with
a network error).

This is the first VIX-term-structure-based strategy in this repo -- a
genuinely different signal class (relative pricing between two implied-vol
indices at different tenors) from every existing price/volume-only
technical indicator already tested.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series

Because this strategy needs a second data series (VIX3M) beyond the single
`price_df` the grid-test harness passes in, `price_df` here is expected to
be the SPY (or other equity) OHLCV frame; VIX and VIX3M are fetched
internally via `data/loaders.py::load_equity` on the fly and aligned by
date. This keeps the required call signature
(`generate_signals(price_df, **params)`) intact for the grid-test harness.
"""

from __future__ import annotations

import sys
import os
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


_vix_cache: dict = {}


def _load_vix_ratio(index: pd.DatetimeIndex) -> pd.Series:
    """Fetch VIX and VIX3M over the span of `index`, return the aligned VIX/VIX3M ratio."""
    from loaders import load_equity

    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()
    key = (start.date(), end.date())
    if key not in _vix_cache:
        vix = load_equity("^VIX", start, end)
        vix3m = load_equity("^VIX3M", start, end)
        vix = vix.set_index("timestamp")["close"].rename("vix") if "timestamp" in vix.columns else vix["close"].rename("vix")
        vix3m = vix3m.set_index("timestamp")["close"].rename("vix3m") if "timestamp" in vix3m.columns else vix3m["close"].rename("vix3m")
        merged = pd.concat([vix, vix3m], axis=1).sort_index()
        merged = merged.ffill()
        ratio = merged["vix"] / merged["vix3m"]
        _vix_cache[key] = ratio
    ratio = _vix_cache[key]
    # Align to the target index (reindex forward-fill, since VIX trades on
    # the same exchange calendar as equities but timestamps may differ).
    return ratio.reindex(index, method="ffill")


def generate_signals(
    price_df: pd.DataFrame,
    smooth_window: int = 5,
    entry_ratio_threshold: float = 1.0,
    exit_ratio_threshold: float = 1.0,
    hold_days: int = 42,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    try:
        ratio = _load_vix_ratio(df.index)
    except Exception:
        # If VIX data isn't available for this asset's date range/exchange
        # (e.g. crypto symbols routed through this same interface by the
        # grid test), there's no valid signal -- stay flat throughout.
        return pd.Series(0, index=close.index, dtype=int)

    smoothed = ratio.rolling(smooth_window).mean()
    in_backwardation = smoothed > entry_ratio_threshold
    resolution_cross = (~in_backwardation) & (in_backwardation.shift(1).fillna(False))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            fresh_onset = bool(smoothed.iloc[i] > entry_ratio_threshold) if not pd.isna(smoothed.iloc[i]) else False
            if held >= hold_days or fresh_onset:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(resolution_cross.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
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
