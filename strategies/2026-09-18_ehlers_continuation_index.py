"""Strategy: Ehlers Continuation Index (CI) trend-onset/exhaustion crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-126):
Per John F. Ehlers' "The Continuation Index" (TASC Sept 2025 Traders' Tips,
https://traders.com/Documentation/FEEDbk_docs/2025/09/TradersTips.html), CI
is the variance-normalized, Inverse-Fisher-Transform-compressed difference
between an UltimateSmoother(price, length/2) and an 8th-order Laguerre
filter (built on UltimateSmoother(price, length)) of the same price series.
When the fast UltimateSmoother pulls away from the slower/laggier Laguerre
filter, CI swings toward +1 (trend continuation / onset); when the two
converge again, CI reverts toward 0 (trend exhaustion). WealthLab's own
disclosed mechanical rule (same Traders' Tips issue): "Buy when CI crosses
above -0.9. Sell when CI crosses below 0." This repo tests that literal
rule long-only on daily bars (source used SPY/ES).

First Continuation Index / Laguerre-minus-UltimateSmoother-difference
strategy in this repo -- distinct from prior standalone Laguerre RSI
(2026-09-05-053/110, a bounded RSI-style oscillator on ONE Laguerre filter)
and Adaptive Laguerre Filter (2026-09-05-058, slope+price-position trend
following on ONE filter's own line) entries, since CI's signal comes from
the DIFFERENCE between two differently-lagged versions of the price series,
normalized by their own rolling variance and IFT-compressed.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _ultimate_smoother(price: np.ndarray, period: float) -> np.ndarray:
    """Ehlers UltimateSmoother (2nd-order recursive highpass-subtraction filter)."""
    n = len(price)
    us = np.zeros(n)
    if period <= 0:
        return price.copy()
    a1 = math.exp(-1.414 * math.pi / period)
    c2 = 2.0 * a1 * math.cos(1.414 * math.pi / period)
    c3 = -a1 * a1
    c1 = (1.0 + c2 - c3) / 4.0
    for i in range(n):
        if i < 3:
            us[i] = price[i]
        else:
            us[i] = (
                (1.0 - c1) * price[i]
                + (2.0 * c1 - c2) * price[i - 1]
                - (c1 + c3) * price[i - 2]
                + c2 * us[i - 1]
                + c3 * us[i - 2]
            )
    return us


def _laguerre_filter(price: np.ndarray, gama: float, order: int, length: float) -> np.ndarray:
    """Ehlers Laguerre filter (built on the UltimateSmoother of price, per
    the TASC Sept 2025 disclosed rule: LG[1] = UltimateSmoother(price, length))."""
    n = len(price)
    smoothed = _ultimate_smoother(price, length)
    out = np.zeros(n)
    # LG[k, 0] = current bar; LG[k, 1] = previous bar. 1-indexed components 1..order.
    lg_cur = np.zeros(order + 1)
    lg_prev = np.zeros(order + 1)
    for t in range(n):
        lg_prev[:] = lg_cur
        lg_cur[1] = smoothed[t]
        for k in range(2, order + 1):
            lg_cur[k] = -gama * lg_prev[k - 1] + lg_prev[k - 1] + gama * lg_prev[k]
        out[t] = lg_cur[1:order + 1].sum() / order
    return out


def _continuation_index(close: pd.Series, gama: float, order: int, length: float) -> pd.Series:
    price = close.to_numpy(dtype=float)
    us = _ultimate_smoother(price, length / 2.0)
    lg = _laguerre_filter(price, gama, order, length)
    diff = np.abs(us - lg)
    variance = pd.Series(diff).rolling(int(length), min_periods=int(length)).mean().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        ref = np.where(variance != 0, 2.0 * (us - lg) / variance, 0.0)
    ci = (np.exp(2.0 * ref) - 1.0) / (np.exp(2.0 * ref) + 1.0)
    return pd.Series(ci, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    gama: float = 0.8,
    order: int = 8,
    length: float = 40,
    buy_level: float = -0.9,
    sell_level: float = 0.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry: CI crosses above buy_level (default -0.9).
    Exit: CI crosses below sell_level (default 0.0).
    (WealthLab's exact disclosed Traders' Tips rule.)
    """
    df = _prep(price_df)
    close = df["close"]

    ci = _continuation_index(close, gama, order, length)
    ci_prev = ci.shift(1)

    buy_cross = (ci_prev <= buy_level) & (ci > buy_level)
    sell_cross = (ci_prev >= sell_level) & (ci < sell_level)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(sell_cross.iloc[i]):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(buy_cross.iloc[i]):
                in_position = True
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
