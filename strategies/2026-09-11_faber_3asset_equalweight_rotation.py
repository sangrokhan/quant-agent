"""Strategy: Meb Faber-style 3-asset equal-weight-if-qualifying rotation
(Stocks/Bonds/Gold), single-asset gate adaptation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-078):
Per QuantifiedStrategies.com's disclosed rule
(https://www.quantifiedstrategies.com/quantitative-trading-strategies/,
visited this iteration; citing Meb Faber's 2015 article), across three
asset classes (Stocks=SPY, Bonds=TLT, Gold=GLD), "invest equally in
whatever is going up (defined as 3-month SMA > 10-month SMA)." If one
asset qualifies, allocate 100% to it; if two qualify, 50/50; if three,
33.33% each. Source's own backtest: average gain per trade 0.77%, annual
return ~12%, max drawdown 26% vs 55% for S&P 500 alone.

This is distinct from the already-tested 5-asset GTAA dual-momentum
(2026-09-11-037/-041, SPY/EFA/EEM/GLD/TLT) in two structural ways: (1)
this Faber construction uses an ABSOLUTE trend filter (3mo SMA vs 10mo
SMA per asset, each asset judged independently) rather than a
CROSS-SECTIONAL rank-and-pick-the-top-1 mechanism; (2) it EQUALLY WEIGHTS
however many of the (here, 3, not 5) assets currently qualify, rather
than concentrating in a single top-ranked pick. Adapted to this repo's
single-asset generate_signals/generate_returns interface: the PRIMARY
asset (SPY) is held with weight = 1/(number of qualifying assets among
{SPY, TLT, GLD}) whenever SPY itself qualifies (its 3mo SMA > 10mo SMA),
and 0 otherwise -- this reproduces exactly the SPY leg's contribution to
the source's own equal-weight construction.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (weight in [0,1])
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_basket_monthly_qualify(index: pd.DatetimeIndex, fast_months: int, slow_months: int) -> pd.DataFrame:
    """Load TLT/GLD via data/loaders.py, compute month-end 'qualifies'
    booleans (3mo SMA > 10mo SMA on monthly closes), aligned to index."""
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity  # noqa: E402

    start = (index.min() - pd.Timedelta(days=400)).to_pydatetime()
    end = (index.max() + pd.Timedelta(days=10)).to_pydatetime()

    out = {}
    for sym in ("TLT", "GLD"):
        df = load_equity(sym, start, end)
        close = df.set_index("timestamp")["close"] if "timestamp" in df.columns else df["close"]
        close.index = pd.to_datetime(close.index).tz_localize(None)
        monthly = close.resample("ME").last().dropna()
        fast = monthly.rolling(fast_months).mean()
        slow = monthly.rolling(slow_months).mean()
        qualifies_monthly = (fast > slow).astype(int)
        qualifies_monthly.index = qualifies_monthly.index + pd.offsets.MonthEnd(0)
        # shift by 1 month (decision at month-end m applies to month m+1)
        qualifies_monthly = qualifies_monthly.shift(1).fillna(0).astype(int)
        daily_index = pd.to_datetime(index).tz_localize(None)
        daily = qualifies_monthly.reindex(daily_index, method="ffill").fillna(0).astype(int)
        daily.index = index
        out[sym] = daily
    return pd.DataFrame(out)


def generate_signals(
    price_df: pd.DataFrame,
    fast_months: int = 3,
    slow_months: int = 8,
) -> pd.Series:
    """Return a [0,1] continuous weight series for the primary asset
    (intended to be run with SPY as price_df)."""
    df = _prep(price_df)
    close = df["close"]

    monthly_primary = close.resample("ME").last().dropna() if hasattr(close.index, "freq") else None
    # Compute primary asset's own monthly qualify flag the same way.
    idx = pd.to_datetime(close.index).tz_localize(None)
    close_reidx = close.copy()
    close_reidx.index = idx
    monthly = close_reidx.resample("ME").last().dropna()
    fast = monthly.rolling(fast_months).mean()
    slow = monthly.rolling(slow_months).mean()
    primary_qualifies_monthly = (fast > slow).astype(int)
    primary_qualifies_monthly.index = primary_qualifies_monthly.index + pd.offsets.MonthEnd(0)
    primary_qualifies_monthly = primary_qualifies_monthly.shift(1).fillna(0).astype(int)
    daily_index = pd.to_datetime(close.index).tz_localize(None)
    primary_qualifies = primary_qualifies_monthly.reindex(daily_index, method="ffill").fillna(0).astype(int)
    primary_qualifies.index = close.index

    basket = _load_basket_monthly_qualify(close.index, fast_months, slow_months)
    num_qualifying = primary_qualifies + basket["TLT"] + basket["GLD"]
    num_qualifying = num_qualifying.replace(0, 1)  # avoid div-by-zero when nobody qualifies (weight will be 0 anyway)

    weight = (primary_qualifies / num_qualifying).astype(float)
    return weight


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Weight-scaled daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    weight = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = weight.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
