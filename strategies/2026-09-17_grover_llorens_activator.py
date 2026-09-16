"""Strategy: Grover Llorens Activator (alexgrover & Lucia Llorens, 2020) --
a Parabolic-SAR-inspired ATR trailing stop, used long-only.

Hypothesis (this cron trigger's iteration 6):
Per the original TradingView publication (confirmed via direct page read,
https://www.tradingview.com/script/UVzC9TOv-Grover-Llorens-Activator-alexgrover-Lucia-Llorens/,
and the companion strategy-analysis post
https://www.tradingview.com/script/VuYM89Tw-Grover-Llorens-Activator-Strategy-Analysis/):
a ratcheting trailing-stop line (`ts`) that converges toward price the
longer a trend persists (addressing the standard trailing-stop weakness of
assuming an infinitely long trend, unlike e.g. this repo's already-tested
Chandelier Exit/SuperTrend variants which use a constant-width ATR band).
Construction: ts starts at price; while price stays above ts, ts ratchets
up to max(ts_prev, price - mult*ATR(length)) (never retreating); once
price crosses below ts, ts flips to track from above using the mirror
rule. Source's own disclosed strategy rule (companion post): "long: closing
price cross over the indicator; short: closing price cross under the
indicator" -- operationalized here long-only (flat instead of short) per
this repo's convention. First Grover Llorens Activator entry in this repo
(0 prior matches), and a distinct construction from this repo's other
ATR-trailing-stop strategies since it converges/decays toward price with
trend persistence rather than maintaining a fixed-width band.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(length).mean()


def _grover_llorens_ts(close: pd.Series, atr_val: pd.Series) -> pd.Series:
    ts = np.full(len(close), np.nan)
    c = close.to_numpy()
    a = atr_val.to_numpy()
    for i in range(len(c)):
        if np.isnan(a[i]):
            continue
        if np.isnan(ts[i - 1]) if i > 0 else True:
            ts[i] = c[i]
            continue
        prev_ts = ts[i - 1]
        if c[i] > prev_ts:
            ts[i] = max(prev_ts, c[i] - a[i])
        else:
            ts[i] = min(prev_ts, c[i] + a[i])
    return pd.Series(ts, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    length: int = 14,
    mult: float = 2.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series: long while close is above
    the Grover Llorens Activator trailing-stop line, flat otherwise."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    atr_val = _atr(high, low, close, length) * mult
    ts = _grover_llorens_ts(close, atr_val)

    position = (close > ts).astype(int)
    position = position.where(ts.notna(), other=0)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
