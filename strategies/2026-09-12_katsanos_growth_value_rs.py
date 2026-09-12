"""Strategy: Katsanos Growth/Value Switching System, simplified single-leg adaptation.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per Markos Katsanos' "Growth Or Value?" (TASC December 2023 Traders' Tips,
summarized at https://www.tradingview.com/scripts/tasc/page-2/): the
market cycles between favoring value (VTV) and growth (VUG) equities. A
rotation system computes each ETF's relative strength (RS) vs a broad
benchmark (SPY), holds whichever ETF currently has the stronger RS, and
blocks NEW entries whenever a Volume Flow Indicator (VFI, a money-
outflow/inflow proxy) signals net money outflow (bear-market risk-off
filter). Exit when the held ETF's RS falls below the other ETF's RS for
`confirm_days` consecutive days AND below its own moving average.

This repo's grid-test harness calls `generate_returns_fn(price_df,
**params)` with ONE price DataFrame per symbol, so this strategy is
implemented as a SINGLE-LEG adaptation: `price_df` is treated as "this
ETF" (e.g. VUG), and its designated pair ETF (VTV) plus the SPY benchmark
are fetched internally via `data/loaders.py` for the RS/VFI comparison.
The resulting position series says whether to be long THIS ETF (not
whichever of the pair currently leads) -- i.e. it tests "should I hold
VUG specifically, using the rotation system's own logic as a signal",
which is a fair single-leg test of whether the RS+VFI construction
produces a genuine edge, even though the source's own system holds
whichever ETF leads (fully deployed at all times as a rotation).

Signal logic
------------
- RS(etf, benchmark, window) = etf.pct_change(window) - benchmark.pct_change(window)
  (a simple relative-strength-vs-benchmark proxy, since the source's exact
  custom RS formula wasn't fully disclosed in the overview text).
- VFI proxy: a Volume Flow Indicator approximation using the sign of
  price change times volume, EMA-smoothed (money-flow-volume style),
  compared to zero.
- Long entry: this ETF's RS > pair ETF's RS AND VFI proxy > 0 (no net
  outflow).
- Exit: this ETF's RS falls below the pair's RS for `confirm_days`
  consecutive days AND close < its own SMA(ma_window), OR a
  `max_hold_days` time-stop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)

Note: `price_df` must be either VUG or VTV (the pair is looked up
automatically); for any other symbol this falls back to a pure
RS-vs-SPY-momentum signal without the pair-rotation comparison.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

_PAIR = {"VUG": "VTV", "VTV": "VUG"}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_series(symbol: str, index: pd.DatetimeIndex) -> pd.DataFrame:
    from loaders import load_equity

    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()
    df = load_equity(symbol, start, end)
    return _prep(df)


def _vfi_proxy(close: pd.Series, volume: pd.Series, window: int = 20) -> pd.Series:
    """Simplified money-flow-volume proxy: sign(price change) * volume,
    EMA-smoothed (a lightweight stand-in for Katsanos' custom VFI)."""
    price_change_sign = np.sign(close.diff().fillna(0.0))
    mfv = price_change_sign * volume
    return mfv.ewm(span=window, adjust=False).mean()


def generate_signals(
    price_df: pd.DataFrame,
    rs_window: int = 20,
    ma_window: int = 40,
    confirm_days: int = 2,
    vfi_window: int = 20,
    max_hold_days: int = 60,
    symbol_hint: str = "VUG",
) -> pd.Series:
    """Return a {0,1} long/flat position series for `price_df`'s own ETF."""
    df = _prep(price_df)
    close, volume = df["close"], df["volume"]

    pair_symbol = _PAIR.get(symbol_hint, None)
    benchmark = _load_series("SPY", close.index)["close"].reindex(close.index, method="ffill")

    rs_self = close.pct_change(rs_window) - benchmark.pct_change(rs_window)

    if pair_symbol is not None:
        pair_close = _load_series(pair_symbol, close.index)["close"].reindex(close.index, method="ffill")
        rs_pair = pair_close.pct_change(rs_window) - benchmark.pct_change(rs_window)
    else:
        rs_pair = pd.Series(0.0, index=close.index)

    vfi = _vfi_proxy(close, volume, vfi_window)
    vfi_favorable = vfi > 0

    sma = close.rolling(ma_window).mean()
    rs_stronger = rs_self > rs_pair

    entry = rs_stronger & vfi_favorable & rs_self.notna() & rs_pair.notna()

    weak_days = (~rs_stronger).astype(int)
    weak_streak = weak_days.groupby((weak_days != weak_days.shift()).cumsum()).cumsum()
    exit_signal = (weak_streak >= confirm_days) & (close < sma)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
