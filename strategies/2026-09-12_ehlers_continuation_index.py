"""Strategy: Ehlers Continuation Index (UltimateSmoother-vs-Laguerre-filter
normalized difference, two-state trend oscillator).

Hypothesis (see knowledge_base id 2026-09-12-173):
Per John F. Ehlers' "Continuation Index" (TASC September 2025 Traders'
Tips), implemented at
https://www.tradingview.com/script/5ZrOut79-TASC-2025-09-The-Continuation-Index/
(full concept disclosure): Ehlers observed that "when price is in trend,
it tends to stay to one side of" a Laguerre filter. The Continuation Index
normalizes the DIFFERENCE between the UltimateSmoother (a low-lag Ehlers
filter, already implemented in this repo's
2026-09-05_ultimate_smoother_trend.py) and a fixed-gamma Laguerre filter
(order-1 classic recursive form) into a two-state oscillator: the source's
own disclosed usage rule is "+1 suggests the trader should position on the
long side. -1 suggests the user should position on the short side." The
UltimateSmoother length is fixed to HALF the Laguerre filter's `length`
input to minimize lag, per the source's own design note.

Long-only adaptation (per SAFETY.md, no short leg): long only when the
Continuation Index state is +1 (UltimateSmoother above the Laguerre
filter); flat otherwise (source's -1 state, which would be a short in the
bidirectional original, is simply "flat" here).

First Ehlers Continuation Index strategy in this repo -- distinct from
Adaptive Laguerre Filter trend (2026-09-05, gamma dynamically adapts per
bar based on tracking error, used AS the trend line directly) and Laguerre
RSI mean-reversion (2026-09-05, RSI-style oscillator on Laguerre-filtered
price) since this indicator instead computes a FIXED-gamma Laguerre filter
purely as a comparison baseline against the UltimateSmoother, deriving a
binary state from their sign difference rather than using either filter's
level or an RSI transform directly.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _ultimate_smoother(price: pd.Series, length: int) -> pd.Series:
    """Ehlers' UltimateSmoother (per TASC's own reference formula, already
    used in this repo's 2026-09-05_ultimate_smoother_trend.py)."""
    f = (1.414 * math.pi) / length
    a1 = math.exp(-f)
    c2 = 2 * a1 * math.cos(f)
    c3 = -a1 * a1
    c1 = (1 + c2 - c3) / 4.0

    values = price.values
    n = len(values)
    us = [0.0] * n
    for i in range(n):
        if i < 2:
            us[i] = values[i]
            continue
        us[i] = (
            (1 - c1) * values[i]
            + (2 * c1 - c2) * values[i - 1]
            - (c1 + c3) * values[i - 2]
            + c2 * us[i - 1]
            + c3 * us[i - 2]
        )
    return pd.Series(us, index=price.index)


def _laguerre_filter(price: pd.Series, gamma: float) -> pd.Series:
    """Ehlers' classic fixed-gamma order-4 Laguerre filter (the standard
    TASC 2000/2025 recursive form, distinct from this repo's *adaptive*-
    gamma Laguerre variant already used elsewhere)."""
    values = price.values.astype(float)
    n = len(values)
    l0 = l1 = l2 = l3 = 0.0
    out = [0.0] * n
    for i in range(n):
        price_i = values[i]
        l0_prev, l1_prev, l2_prev, l3_prev = l0, l1, l2, l3
        l0 = (1 - gamma) * price_i + gamma * l0_prev
        l1 = -gamma * l0 + l0_prev + gamma * l1_prev
        l2 = -gamma * l1 + l1_prev + gamma * l2_prev
        l3 = -gamma * l2 + l2_prev + gamma * l3_prev
        out[i] = (l0 + 2 * l1 + 2 * l2 + l3) / 6.0
    return pd.Series(out, index=price.index)


def generate_signals(
    price_df: pd.DataFrame,
    gamma: float = 0.5,
    length: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    us_length = max(2, length // 2)
    us = _ultimate_smoother(close, us_length)
    laguerre = _laguerre_filter(close, gamma)

    diff = us - laguerre
    smoothed_diff = diff.rolling(max(2, length // 4)).mean()

    state_long = (smoothed_diff > 0).fillna(False)
    position = state_long.astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    gamma: float = 0.5,
    length: int = 20,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs here)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(price_df, gamma=gamma, length=length)

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    return strat_returns
