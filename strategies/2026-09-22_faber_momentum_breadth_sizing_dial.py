"""Strategy: Meb Faber Three-Way Momentum breadth as a position-sizing dial.

Hypothesis (see knowledge_base/strategies_log.jsonl, this iteration's id):
Per QuantifiedStrategies.com's "Meb Faber's Momentum and Trend-Following
Trading Strategy Explained (Gold, Stocks, And Bonds)"
(https://www.quantifiedstrategies.com/meb-faber-momentum-trend-following-strategy/,
Mebane Faber, 2015 whitepaper based on Ned Davis Research), a simple monthly
momentum rule -- an asset's 3-month SMA above its 10-month SMA -- applied
independently across three uncorrelated asset classes (stocks/SPY,
bonds/TLT, gold/GLD) and then equal-weighted across whichever pass, produces
a defensive, low-drawdown multi-asset portfolio (source's own backtest:
13.12% CAGR 1971-2015, MDD only -21.4% vs -50.95% stocks-alone).

This repo cannot literally replicate Faber's 3-asset dynamically-reallocated
PORTFOLIO within the single-price-series generate_returns(price_df) contract
(Step 5 requires one traded asset's return series). Instead we operationalize
the source's core "breadth of momentum confirmation across asset classes"
insight as a POSITION-SIZING DIAL applied to whatever asset is being traded
in the grid test: compute the monthly 3mo/10mo-SMA breadth count (0-3) across
the fixed macro basket {SPY, TLT, GLD} every month, and size the traded
asset's daily exposure as breadth_count/3 (0%, 33%, 67%, or 100%), requiring
breadth_count >= min_breadth to take ANY exposure at all. This is distinct
from all prior single-asset SMA-crossover trend filters and from the
SPY/TLT 2-asset ratio regime filter (2026-09-05-035) and the Fabian 3-way
EQUITY-ONLY intermarket voting filter (this same iteration's other test,
2026-09-22-124) via using a genuinely cross-asset-class (equity+bond+gold)
breadth signal as a continuous SIZING dial rather than a binary equity-only
vote.

Signal logic
------------
- Resample SPY, TLT, GLD closes to monthly (month-end) frequency.
- For each, 3-month SMA vs 10-month SMA -> momentum flag (1 if 3mo>10mo).
- breadth_count = sum of the three flags (0-3) each month.
- Traded-asset exposure (fractional, not just 0/1) = breadth_count/3 if
  breadth_count >= min_breadth else 0.0.
- Forward-fill the monthly sizing dial onto the daily price_df index of
  whatever asset is being traded.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (fractional [0,1] exposure)
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity  # noqa: E402

_breadth_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def _monthly_momentum_flag(close: pd.Series, fast_months: int, slow_months: int) -> pd.Series:
    monthly = close.resample("ME").last().dropna()
    fast = monthly.rolling(fast_months, min_periods=fast_months).mean()
    slow = monthly.rolling(slow_months, min_periods=slow_months).mean()
    return (fast > slow).astype(float)


def _get_breadth_dial(
    start: pd.Timestamp, end: pd.Timestamp, fast_months: int, slow_months: int, min_breadth: int
) -> pd.Series:
    """Monthly fractional exposure dial [0, 1/3, 2/3, 1] from SPY/TLT/GLD momentum breadth, cached."""
    key = (start.date().isoformat(), end.date().isoformat(), fast_months, slow_months, min_breadth)
    if key in _breadth_cache:
        return _breadth_cache[key]

    fetch_start = datetime(max(start.year - 3, 2000), 1, 1, tzinfo=timezone.utc)
    fetch_end = datetime(end.year + 1, 1, 1, tzinfo=timezone.utc)

    flags = {}
    for sym in ("SPY", "TLT", "GLD"):
        df = load_equity(sym, fetch_start, fetch_end)
        s = df.set_index(pd.to_datetime(df["timestamp"], utc=True))["close"]
        s = s[~s.index.duplicated(keep="first")].sort_index()
        flags[sym] = _monthly_momentum_flag(s, fast_months, slow_months)

    flags_df = pd.DataFrame(flags).dropna(how="any")
    breadth_count = flags_df.sum(axis=1)
    dial = (breadth_count / 3.0).where(breadth_count >= min_breadth, 0.0)

    _breadth_cache[key] = dial
    return dial


def generate_signals(
    price_df: pd.DataFrame,
    fast_months: int = 3,
    slow_months: int = 10,
    min_breadth: int = 1,
) -> pd.Series:
    """Return a fractional [0,1] exposure series from the Faber momentum-breadth dial."""
    df = _prep(price_df)
    idx = df.index

    monthly_dial = _get_breadth_dial(idx.min(), idx.max(), fast_months, slow_months, min_breadth)
    dial = monthly_dial.reindex(idx, method="ffill").fillna(0.0)
    return dial


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted (fractional) daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
