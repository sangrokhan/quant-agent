"""Strategy: REIT ETF Trading System (Katsanos), simplified daily-bar adaptation.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per Markos Katsanos' "Is The Price REIT?" (TASC June 2024 Traders' Tips,
fully disclosed strategy at
https://www.tradingview.com/script/gkp6SIlb-TASC-2024-06-REIT-ETF-Trading-System/):
REIT ETFs (e.g. VNQ) are sensitive to interest rates (inversely) and
correlated with the broader equity market; a REIT-specific system should
combine (1) a Bollinger-Band oversold-bounce entry, (2) a Donchian-channel
uptrend-breakout entry, and (3) a rate-sensitivity gate using the 10-Year
Treasury Yield (^TNX) -- entries favored when yields are falling/low or
weakly correlated with the REIT ETF (a falling-rate tailwind), since REITs
often move inversely to rates. This strategy adapts the source's weekly
multi-condition system into a simplified DAILY-bar version keeping the
core dual-entry logic and the TNX rate-sensitivity gate, using a chandelier
stop for exits (the source's simplest, most portable exit rule) rather
than the full multi-branch exit stack.

Signal logic
------------
- Oversold entry: close < lower Bollinger Band (bb_window, bb_std) AND
  close > close.shift(1) (a bounce day) AND TNX 20-day ROC <= tnx_roc_max
  (rates falling/flat -- rate-sensitivity tailwind).
- Uptrend entry: close crosses above its own prior `donchian_window`-day
  Donchian high AND TNX 20-day ROC <= tnx_roc_max.
- Exit: chandelier stop -- close falls more than `atr_mult` * ATR(14)
  below the highest close of the last `chandelier_window` days, OR a
  `max_hold_days` time-stop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, tnx_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, tnx_df, **params) -> pd.Series  (daily strategy returns)

Note: unlike most strategies in this repo, this one needs a SECOND price
series (the 10-Year Treasury Yield, ^TNX) as a rate-sensitivity gate. To
keep the standard `generate_signals(price_df, **params)` /
`generate_returns(price_df, **params)` contract required by the grid-test
harness (which calls these with only one price DataFrame), ^TNX is fetched
internally via `data/loaders.py::load_equity("^TNX", ...)`, spanning the
same date range as `price_df`, and cached per-call.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_tnx(index: pd.DatetimeIndex) -> pd.Series:
    from loaders import load_equity

    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()
    tnx_df = load_equity("^TNX", start, end)
    tnx_df = _prep(tnx_df)
    return tnx_df["close"].reindex(index, method="ffill")


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()


def generate_signals(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    donchian_window: int = 40,
    tnx_roc_window: int = 20,
    tnx_roc_max: float = 0.0,
    chandelier_window: int = 10,
    atr_mult: float = 2.0,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close, high, low = df["close"], df["high"], df["low"]

    tnx = _load_tnx(close.index)
    tnx_roc = tnx.pct_change(tnx_roc_window)
    rate_favorable = (tnx_roc <= tnx_roc_max) & tnx_roc.notna()

    sma = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()
    lower_band = sma - bb_std * std
    oversold_entry = (close < lower_band) & (close > close.shift(1)) & rate_favorable

    donchian_high = high.rolling(donchian_window).max().shift(1)
    uptrend_entry = (close > donchian_high) & (close.shift(1) <= donchian_high.shift(1)) & rate_favorable

    entry = oversold_entry | uptrend_entry

    atr14 = _atr(high, low, close, 14)
    highest_close = close.rolling(chandelier_window).max()
    chandelier_stop = highest_close - atr_mult * atr14
    exit_signal = close < chandelier_stop

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
