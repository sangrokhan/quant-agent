"""Strategy: Equity Trend-Following Gated by TLT's Own Absolute Level vs its MA.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-26-016):
Per QuantifiedStrategies.com's "Stocks vs. Bonds: What History Says When
Bonds Decline" (https://quantifiedstrategies.substack.com/p/stocks-vs-bonds-what-history-says-when-bonds-decline,
free disclosed finding, full numeric trading-rule table paywalled but the
core mechanic and one illustrative example fully disclosed): when TLT
trades BELOW its own moving average (bond prices falling / rates rising),
subsequent equity (SPY) performance is historically weak (source's own
15-day-MA example: 421 trades since 2003, only 2.37% CAGR, 50% MDD when
staying invested during TLT-below-MA periods) -- "flipping the logic,
owning stocks when bonds are strong (TLT above its MA) produced
significantly better results." This strategy implements the FLIPPED
(source-recommended) version directly: gate the primary equity asset's own
close>SMA(trend_window) trend-following signal to be long ONLY when TLT's
own close is ALSO above TLT's own rolling SMA(tlt_ma_window) (bonds
strong/rates falling regime); flat otherwise.

Distinct from every other TLT-based cross-asset gate already tested in
this repo (SPY/TLT RATIO SMA crossover 2026-09-05-036, TLT/IEF duration
ratio 2026-09-11-045, GLD/TLT ratio 2026-09-11-031, Network Momentum
single-edge spillover 2026-09-08-143) -- this uses TLT's own ABSOLUTE
price level vs its own moving average as a binary macro regime gate
(not a ratio against another asset, not TLT's own momentum/return), which
is exactly the mechanic QuantifiedStrategies' own article describes and
recommends as the "flipped" (better) version of their finding.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, tlt_price_df, **params) -> pd.Series
    generate_signals(price_df, tlt_price_df, **params) -> pd.Series ({0,1})

NOTE: this strategy needs a SECOND price series (TLT) not just price_df.
Since grid_test.py/generate_returns_fn contract only passes a single
price_df, TLT data is fetched internally via data/loaders.py at import
time (module-level cache) so the standard single-price_df signature still
works for the grid harness.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

_tlt_cache: dict = {}


def _get_tlt(start=None, end=None) -> pd.DataFrame:
    key = "TLT"
    if key not in _tlt_cache:
        import sys
        import os

        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
        from loaders import load_equity

        _tlt_cache[key] = load_equity("TLT", datetime(2010, 1, 1), datetime(2026, 12, 31), interval="1d")
    return _tlt_cache[key]


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 100,
    tlt_ma_window: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    trend_ok = close > close.rolling(trend_window).mean()

    tlt_df = _prep(_get_tlt())
    tlt_close = tlt_df["close"]
    tlt_ma = tlt_close.rolling(tlt_ma_window).mean()
    tlt_strong = (tlt_close > tlt_ma).reindex(close.index, method="ffill").fillna(False)

    position = (trend_ok & tlt_strong).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
