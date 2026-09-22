"""Strategy: SMA trend-following on equities, gated by a yield-curve
steepening regime filter (10Y minus 3M Treasury slope).

Hypothesis (see knowledge_base/strategies_log.jsonl, this iteration's id):
Per quantmemo.com's "Systematic Yield Curve Steepener" strategy breakdown
(https://quantmemo.com/strategies/yield-curve-steepener, read this
iteration via browser_exec), the yield curve inverts (short yields exceed
long yields) when the central bank has pushed short rates high to fight
inflation while the bond market prices in a future slowdown/cuts.
Inversions historically resolve via steepening once the hiking cycle
visibly ends -- and per the source's OWN "confirmation" rule ("require
that the curve has stopped flattening, e.g. spread is above its own
recent short-term average, before entering... this one rule prevents a
large share of historical losses"), the transition from inverted/flat to
actively re-steepening is a macro regime marker distinct from the
inversion level itself. This strategy translates that fixed-income-trade
thesis into an EQUITY regime filter (since this repo's data/loaders.py
only supports single-instrument OHLCV, not a genuine duration-neutral
2s10s futures spread trade, which is feasibility-blocked here): gate a
plain SMA(fast)/SMA(slow) trend-following long entry on SPY/QQQ to fire
ONLY when the 10Y-3M Treasury slope (^TNX close - ^IRX close, both fetched
via data/loaders.py -- no new data-fetching logic, same yfinance provider)
is BOTH below its own trailing slope_lookback-day historical percentile
threshold (i.e. curve is unusually flat/inverted by recent-history
standards) AND rising over confirm_window days (steepening has started,
per the source's own "stopped flattening" confirmation rule) -- the
"opportunity" window the source describes, as distinct from "still
inverted and still flattening" which the source calls "a trap."

Signal logic
------------
- slope = ^TNX close - ^IRX close (10Y minus 3M), loaded via load_equity
  and reindexed/forward-filled onto the target instrument's price index.
- flat_or_inverted = slope <= its own trailing slope_lookback-day rolling
  percentile (slope_percentile, e.g. 25th percentile = "bottom quartile
  of recent history", not just <0 to allow for genuinely flat regimes).
- steepening = slope > slope.shift(confirm_window) (curve has widened
  over the last confirm_window trading days -- the source's own
  "stopped flattening" confirmation test, implemented directly rather
  than via a short-term moving average per the source's own suggested
  simplification).
- Entry (long): close crosses above SMA(fast) while SMA(fast)>SMA(slow)
  (plain trend confirmation) AND flat_or_inverted AND steepening, all on
  the same bar.
- Exit: close crosses back below SMA(fast), OR max_hold_days time-stop.
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
    return df.sort_index()


_slope_cache: dict = {}


def _get_slope_series(index: pd.DatetimeIndex) -> pd.Series:
    """Fetch/cache the 10Y-3M Treasury slope and align to `index`."""
    from loaders import load_equity

    key = (index.min(), index.max())
    if key not in _slope_cache:
        start = index.min().to_pydatetime() if hasattr(index.min(), "to_pydatetime") else datetime(2015, 1, 1)
        end = index.max().to_pydatetime() if hasattr(index.max(), "to_pydatetime") else datetime.utcnow()
        tnx = load_equity("^TNX", datetime(2015, 1, 1), end, interval="1d")
        irx = load_equity("^IRX", datetime(2015, 1, 1), end, interval="1d")
        tnx = tnx.set_index("timestamp")["close"] if "timestamp" in tnx.columns else tnx["close"]
        irx = irx.set_index("timestamp")["close"] if "timestamp" in irx.columns else irx["close"]
        slope = (tnx - irx).sort_index()
        _slope_cache[key] = slope
    slope = _slope_cache[key]
    aligned = slope.reindex(index.union(slope.index)).sort_index().ffill().reindex(index)
    return aligned


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 20,
    slow_window: int = 50,
    slope_lookback: int = 504,
    slope_percentile: float = 0.25,
    confirm_window: int = 20,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma_fast = close.rolling(fast_window).mean()
    sma_slow = close.rolling(slow_window).mean()
    trend_up = (close > sma_fast) & (sma_fast > sma_slow)

    slope = _get_slope_series(close.index)
    slope_threshold = slope.rolling(slope_lookback, min_periods=60).quantile(slope_percentile)
    flat_or_inverted = (slope <= slope_threshold).fillna(False)
    steepening = (slope > slope.shift(confirm_window)).fillna(False)

    entry = trend_up.fillna(False) & flat_or_inverted & steepening
    exit_trend = ~((close > sma_fast)).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trend.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
