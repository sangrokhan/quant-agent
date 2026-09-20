"""Strategy: XLI/XLU (Industrials vs Utilities) sector-rotation ROC gate on
QQQ/SPY trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-XXX):
Per https://alphamancy.com/learn/sector-rotation ("Sector Rotation: XLY vs
XLP"), which explicitly lists "Industrials (XLI) vs. Utilities (XLU) --
Manufacturing growth vs. defensive yield" as one of several standard
cyclical-vs-defensive rotation pairs macro analysts watch (alongside the
already-tested-and-accepted XLY/XLP pair, 2026-09-05-038). We adapt the
source's own stated Alphameter METHODOLOGY for its XLY/XLP signal --
"compute the ratio and its 20-day rate of change; normalize against
historical range; a sharply rising ROC maps to risk-on, sharply falling to
risk-off" -- to the XLI/XLU pair instead, which is a distinct sector pair
from anything tested in this repo (10 prior XLY/XLP or XLU/SPY hits, none
on the XLI/XLU pair specifically), and uses a rate-of-change-of-ratio
construction rather than the SMA-crossing construction used for the
already-accepted XLY/XLP entry (a deliberately different gating rule, not
just a different pair, to test whether the source's own preferred ROC
methodology transfers).

Signal logic:
1. Compute ratio = XLI_close / XLU_close.
2. roc = ratio.pct_change(roc_window) (default 20 trading days, per
   source).
3. Risk-on regime: roc > roc_threshold (ratio accelerating upward --
   industrials outperforming utilities, i.e. manufacturing/cyclical
   confidence building).
4. Long the underlying (QQQ or SPY) while close > SMA(trend_window) AND
   risk-on regime holds; flat otherwise.

First XLI/XLU strategy in this repo -- distinct from the already-accepted
XLY/XLP SMA-crossing gate (2026-09-05-038) and XLU/SPY beta-rotation ROC
gate (2026-09-05-067) via being a different cyclical/defensive sector PAIR
(Industrials vs Utilities rather than Discretionary vs Staples, or
Utilities vs the broad index itself).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1})
    generate_returns(price_df, **params) -> pd.Series
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity  # noqa: E402

_ratio_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _xli_xlu_ratio(price_index: pd.DatetimeIndex) -> pd.Series:
    cache_key = "xli_xlu"
    if cache_key not in _ratio_cache:
        start = datetime(2015, 1, 1)
        end = datetime(2027, 1, 1)
        xli = load_equity("XLI", start=start, end=end)
        xlu = load_equity("XLU", start=start, end=end)
        xli = xli.set_index("timestamp")["close"] if "timestamp" in xli.columns else xli["close"]
        xlu = xlu.set_index("timestamp")["close"] if "timestamp" in xlu.columns else xlu["close"]
        ratio = (xli / xlu).dropna()
        _ratio_cache[cache_key] = ratio
    ratio = _ratio_cache[cache_key]
    return ratio.reindex(price_index, method="ffill")


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 100,
    roc_window: int = 20,
    roc_threshold: float = 0.0,
) -> pd.Series:
    """Long the underlying while close > SMA(trend_window) AND the
    XLI/XLU ratio's roc_window-day rate of change exceeds roc_threshold
    (risk-on cyclical rotation)."""
    df = _prep(price_df)
    close = df["close"]
    trend_long = close > close.rolling(trend_window).mean()

    ratio = _xli_xlu_ratio(df.index)
    roc = ratio.pct_change(roc_window)
    risk_on = roc > roc_threshold

    position = (trend_long.fillna(False) & risk_on.fillna(False)).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
