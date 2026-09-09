"""Strategy: XLE trend-following gated by USO (crude oil) momentum confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-029):
Energy-sector equities (XLE) are economically driven by crude oil prices,
but multiple comparison sources (e.g. "XLE vs USO: Energy Stocks or Direct
Crude Oil Exposure?", "Energy: USO and XLE Have Opposite Short Patterns")
note that USO (direct crude oil exposure) tends to be the more volatile,
faster-moving leg while XLE (energy equities) lags/dampens the same
underlying oil-price move. No single source discloses a concrete numeric
trading rule, so this strategy is self-constructed but fully disclosed:
a plain SMA trend-following signal on XLE, gated by requiring USO's own
trailing momentum to also be positive (crude-oil confirmation of the
energy-equity trend) -- analogous to the cross-asset confirmation-gate
pattern already used elsewhere in this repo (e.g. multi-timeframe/dual-
asset momentum gates), first applied here to the energy-equity/crude-oil
pair specifically.

Signal logic
------------
- Long entry: close(XLE) > SMA(trend_window) on XLE AND USO's trailing
  momentum (pct_change over mom_window days) is positive.
- Exit: close(XLE) crosses back below its own SMA(trend_window), OR USO's
  trailing momentum turns negative (confirmation breaks), OR a
  max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily returns)

Note: price_df passed in is XLE; USO is fetched internally.
"""

from __future__ import annotations

import os
import sys
from datetime import timedelta

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_uso_aligned(index: pd.DatetimeIndex) -> pd.Series:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity  # noqa: E402

    start = index.min() - timedelta(days=10)
    end = index.max() + timedelta(days=2)
    uso_df = load_equity("USO", start.to_pydatetime() if hasattr(start, "to_pydatetime") else start,
                          end.to_pydatetime() if hasattr(end, "to_pydatetime") else end)
    uso_df = _prep(uso_df)
    close = uso_df["close"]
    aligned = close.reindex(index.union(close.index)).sort_index().ffill().reindex(index)
    return aligned


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    mom_window: int = 20,
    max_hold_days: int = 30,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(trend_window).mean()
    uso_close = _load_uso_aligned(df.index)
    uso_mom = uso_close.pct_change(mom_window)

    entry = (close > sma) & (uso_mom > 0).fillna(False)
    exit_trend = close < sma
    exit_confirm = (uso_mom <= 0).fillna(True)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trend.iloc[i]) or bool(exit_confirm.iloc[i]) or held >= max_hold_days:
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
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
