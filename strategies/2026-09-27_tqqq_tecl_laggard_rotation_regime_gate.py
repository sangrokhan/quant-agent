"""Strategy: TQQQ/TECL 3-Day Laggard Rotation with QQQ Trend Regime Gate.

Hypothesis (2026-09-27 KB entry, this iteration): per
https://finlab.finance/en/blog/us-mean-reversion-strategy ("Short-Term Mean
Reversion Trading Strategy Backtest: The 3-Day Laggard Rule Behind a 67%
CAGR"), a fully disclosed 3-layer rule: (1) risk-on regime when QQQ is
above its 200-day SMA AND QQQ's trailing 126-day return is positive; (2) in
risk-on, hold whichever of TQQQ (3x Nasdaq-100) or TECL (3x tech sector)
lagged over the last 3 trading days (mean-reversion/liquidity-provision
thesis: temporary flow imbalance between two heavily-overlapping leveraged
ETFs, not genuine leadership change); (3) in risk-off, rotate to a
defensive sleeve (simplified here to flat, matching this repo's existing
simplification convention for multi-asset rotation systems, e.g.
2026-09-11-070 TQQQ/TMF). Source's own 2016-2026 backtest: CAGR 67.4%,
Sharpe 1.43, MDD -27.6%.

Architecture note: this repo's generate_signals/generate_returns contract
takes ONE primary price_df. This strategy adapts the two-leg rotation into
that contract by treating TQQQ as price_df's own symbol (the caller passes
TQQQ's OHLCV) and loading TECL internally for the 3-day-laggard comparison
-- i.e. this file specifically answers "should I hold TQQQ" rather than
implementing the full two-way rotation (that would require holding TECL on
days when TECL is the laggard instead, which this single-asset contract
cannot express without a portfolio-level backtest engine). This means the
tested returns UNDERSTATE the source's own full-rotation result (this
version is flat, not long TECL, whenever TECL was the laggard) -- an
honest, conservative simplification, not a faithful reproduction.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import sys
import os
from datetime import datetime, timezone

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

_other_leg_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_other_leg_close(index: pd.DatetimeIndex, other_symbol: str) -> pd.Series:
    cache_key = other_symbol
    if cache_key in _other_leg_cache:
        close = _other_leg_cache[cache_key]
    else:
        from loaders import load_equity

        start = index.min().to_pydatetime() if len(index) else datetime(2015, 1, 1)
        end = index.max().to_pydatetime() if len(index) else datetime(2026, 9, 1)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        pad_start = start.replace(year=max(start.year - 1, 2013))
        close = _prep(load_equity(other_symbol, pad_start, end))["close"]
        _other_leg_cache[cache_key] = close

    return close.reindex(index, method="ffill")


def _load_regime_gate(index: pd.DatetimeIndex, regime_sma_window: int, regime_return_window: int) -> pd.Series:
    cache_key = ("regime", regime_sma_window, regime_return_window)
    if cache_key in _other_leg_cache:
        gate = _other_leg_cache[cache_key]
    else:
        from loaders import load_equity

        start = index.min().to_pydatetime() if len(index) else datetime(2015, 1, 1)
        end = index.max().to_pydatetime() if len(index) else datetime(2026, 9, 1)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        pad_start = start.replace(year=max(start.year - 2, 2013))

        qqq_close = _prep(load_equity("QQQ", pad_start, end))["close"]
        above_sma = qqq_close > qqq_close.rolling(regime_sma_window).mean()
        pos_return = qqq_close.pct_change(regime_return_window) > 0
        gate = (above_sma & pos_return).astype(int)
        _other_leg_cache[cache_key] = gate

    return gate.reindex(index, method="ffill").fillna(0).astype(int)


def generate_signals(
    price_df: pd.DataFrame,
    other_symbol: str = "TECL",
    lag_window: int = 3,
    regime_sma_window: int = 200,
    regime_return_window: int = 126,
) -> pd.Series:
    """Return a {0,1} long/flat position series for the primary asset
    (assumed to be TQQQ or TECL, whichever price_df represents).

    Long when: QQQ risk-on regime is active (close > SMA(regime_sma_window)
    AND regime_return_window-day return > 0) AND the primary asset's
    trailing lag_window-day return is LOWER than the other_symbol's
    trailing lag_window-day return (primary asset is the laggard -> buy
    it, expecting mean reversion). Flat otherwise (including risk-off,
    matching this repo's simplified-defensive-sleeve convention).
    """
    df = _prep(price_df)
    close = df["close"]

    own_lag_return = close.pct_change(lag_window)
    other_close = _load_other_leg_close(df.index, other_symbol)
    other_lag_return = other_close.pct_change(lag_window)

    primary_is_laggard = (own_lag_return < other_lag_return).fillna(False)
    regime_gate = _load_regime_gate(df.index, regime_sma_window, regime_return_window)

    position = (primary_is_laggard.astype(int) & regime_gate).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)
    position = generate_signals(price_df, **kwargs)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
