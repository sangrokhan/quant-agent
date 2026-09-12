"""Strategy: ATR-Adaptive-Gamma Laguerre Filter trend following.

Source: runbacktest.com's "Adaptive Laguerre Filter" trading-strategy doc
(https://runbacktest.com/trading-strategies/adaptive-laguerre-filter, read
this iteration via browser_exec -- web_search DDGS backend returned "No
results found" on the first query attempted this iteration, so the Bing
SERP fallback was used for the whole iteration). Disclosed rule:

    ATR = EMA-based Average True Range (atr_period)
    atr_pct = 100 * ATR / close
    normalized = clip(atr_pct / atr_threshold_percent, 0, 1)
    gamma = gamma_max - normalized * (gamma_max - gamma_min)
        (gamma near gamma_max in quiet/low-ATR% regimes -> extra smoothing;
         gamma near gamma_min when ATR% is elevated -> low-lag responsiveness)
    Four-pole Laguerre filter (Ehlers' standard cascade, using this
    per-bar-varying gamma instead of a fixed constant):
        L0 = (1-gamma)*price + gamma*L0[1]
        L1 = -gamma*L0 + L0[1] + gamma*L1[1]
        L2 = -gamma*L1 + L1[1] + gamma*L2[1]
        L3 = -gamma*L2 + L2[1] + gamma*L3[1]
        Laguerre = (L0 + 2*L1 + 2*L2 + L3) / 6
    Entry/exit: price-vs-Laguerre crossover plus a slope confirmation.

This is architecturally distinct from the already-accepted 2026-09-05-058
Adaptive Laguerre Filter (which used Ehlers' own INSTANTANEOUS-PHASE
feedback mechanism per quantifiedstrategies.com to adapt gamma, not an ATR%
threshold) -- here gamma is driven purely by realized-volatility regime
(ATR% of price) rather than a cycle-phase feedback loop, making this a
genuinely different adaptive-smoothing construction sharing only the
4-pole Laguerre cascade shape. 0 prior "ATR-adaptive gamma Laguerre"
entries in this repo's knowledge base (distinct from Laguerre RSI
2026-09-05-053/2026-09-06-110 and instantaneous-adaptive Laguerre
2026-09-05-058/065/066).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's
id): Driving the Laguerre filter's smoothing directly off realized
volatility (ATR%) should make it track price closely exactly when trends
are moving fast (high ATR% -> low gamma -> responsive), while damping noise
during quiet, range-bound stretches (low ATR% -> high gamma -> smooth) --
a more direct volatility-regime-driven adaptation than Ehlers' own
phase-feedback approach, which may generalize differently across equity
vs. crypto's very different volatility regimes.

Signal logic
------------
- Long when close crosses above the Laguerre line AND the Laguerre line's
  own slope_lookback-bar slope is positive (source's "slope confirmation").
- Exit on mirror cross-under, slope turning negative, or a max_hold_days
  time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} long/flat position series aligned to price_df.index.
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


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False, min_periods=period).mean()


def _adaptive_laguerre(
    close: pd.Series,
    atr: pd.Series,
    gamma_min: float,
    gamma_max: float,
    atr_threshold_percent: float,
) -> pd.Series:
    n = len(close)
    price = close.values
    atr_pct = (100.0 * atr / close).values

    l0 = np.zeros(n)
    l1 = np.zeros(n)
    l2 = np.zeros(n)
    l3 = np.zeros(n)
    out = np.full(n, np.nan)

    for i in range(n):
        if np.isnan(atr_pct[i]):
            continue
        normalized = min(max(atr_pct[i] / atr_threshold_percent, 0.0), 1.0)
        gamma = gamma_max - normalized * (gamma_max - gamma_min)

        p0 = l0[i - 1] if i > 0 else price[i]
        p1 = l1[i - 1] if i > 0 else price[i]
        p2 = l2[i - 1] if i > 0 else price[i]
        p3 = l3[i - 1] if i > 0 else price[i]

        l0[i] = (1 - gamma) * price[i] + gamma * p0
        l1[i] = -gamma * l0[i] + p0 + gamma * p1
        l2[i] = -gamma * l1[i] + p1 + gamma * p2
        l3[i] = -gamma * l2[i] + p2 + gamma * p3

        out[i] = (l0[i] + 2 * l1[i] + 2 * l2[i] + l3[i]) / 6.0

    return pd.Series(out, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    atr_period: int = 14,
    gamma_min: float = 0.2,
    gamma_max: float = 0.9,
    atr_threshold_percent: float = 3.0,
    slope_lookback: int = 5,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    atr = _atr(df, atr_period)
    laguerre = _adaptive_laguerre(close, atr, gamma_min, gamma_max, atr_threshold_percent)

    slope = laguerre - laguerre.shift(slope_lookback)
    above = (close > laguerre).fillna(False)
    rising = (slope > 0).fillna(False)

    cross_up = above & (~above.shift(1).fillna(False))
    cross_down = (~above) & (above.shift(1).fillna(False))

    entry_cond = (cross_up & rising).fillna(False)
    exit_cond = (cross_down | (~rising)).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cond.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_cond.iloc[i]):
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
