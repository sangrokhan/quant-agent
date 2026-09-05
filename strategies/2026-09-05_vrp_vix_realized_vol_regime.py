"""Strategy: Volatility Risk Premium (VRP = VIX - realized vol) regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-044):
The Volatility Risk Premium (VRP) is the spread between the market's
option-implied 30-day volatility expectation (VIX) and the actual realized
volatility of the underlying over a recent lookback window. Per Google's
AI-overview synthesis (citing Robot Wealth, Concretum Group, Invest with
CARL, FlashAlpha, Charles Schwab, StrikeWatch EA): VRP = VIX -
annualized_realized_vol(lookback). A positive VRP (options pricing MORE
turbulence than has actually occurred, e.g. VIX exceeding realized vol by a
threshold of +2 to +4 vol points) signals a risk-on/"volatility overpriced"
regime historically associated with calmer, more favorable equity
conditions (a persistent structural premium sellers of volatility harvest);
a negative or shrinking VRP (realized vol catching up to or exceeding VIX)
signals an acute/emerging shock where actual turbulence is outpacing
expectations -- a risk-off signal. Implemented here as a long/flat equity
exposure gate (not options/ETP trading, per this repo's long-only
equity/crypto backtesting scope): long when VRP > vrp_threshold, flat
otherwise. First VIX-minus-realized-volatility-SPREAD strategy in this
repo -- distinct from prior VIX-level-threshold strategies (VIX Bollinger
Band 2026-09-04-103, CVR3 2026-09-05-021) and the VIX/VIX3M term-structure
strategy (2026-09-04-157, 2026-09-05-028), all of which use VIX levels/
ratios directly rather than the VIX-vs-realized-vol spread.

Signal logic
------------
- Fetch ^VIX daily closes via data/loaders.py load_equity("^VIX", ...)
  internally (mirrors the DXY/HYG-LQD/MOVE strategies' cross-asset-signal
  pattern for macro data not present in price_df itself).
- realized_vol = annualized rolling std of price_df's OWN daily log returns
  over `rv_window` days (the underlying being traded, not necessarily SPY --
  this makes the signal genuinely per-asset when applied to QQQ, BTC, etc.,
  even though VIX itself measures S&P 500 options).
- VRP = VIX - realized_vol (both in annualized vol-percentage-point terms).
- Long when VRP > vrp_threshold (options pricing meaningfully more
  turbulence than realized -- calmer risk-on regime); flat when VRP <=
  vrp_threshold (realized vol catching up to/exceeding implied -- risk-off).

Interface contract for validators (see validation/validators.py) and grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
"""

from __future__ import annotations

import math
import sys
import os

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_vix_series(idx: pd.DatetimeIndex) -> pd.Series:
    """Fetch ^VIX closes, reindexed/ffilled onto the strategy's own trading-day index."""
    from loaders import load_equity

    start = (idx.min() - pd.Timedelta(days=30)).to_pydatetime()
    end = (idx.max() + pd.Timedelta(days=5)).to_pydatetime()

    vix = load_equity("^VIX", start, end).set_index("timestamp")["close"].sort_index()
    vix.index = vix.index.tz_localize(None) if vix.index.tz is not None else vix.index

    target_idx = idx.tz_localize(None) if getattr(idx, "tz", None) is not None else idx
    vix = vix.reindex(vix.index.union(target_idx)).sort_index().ffill()
    vix = vix.reindex(target_idx)
    vix.index = idx
    return vix


def generate_signals(
    price_df: pd.DataFrame,
    rv_window: int = 20,
    vrp_threshold: float = 2.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    idx = df.index

    try:
        vix = _get_vix_series(idx)
    except Exception:
        return pd.Series(0, index=idx, dtype=int)

    daily_log_ret = (close / close.shift(1)).apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol_pct = daily_log_ret.rolling(rv_window).std() * (252 ** 0.5) * 100.0

    vrp = vix - realized_vol_pct
    position = (vrp > vrp_threshold).fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
