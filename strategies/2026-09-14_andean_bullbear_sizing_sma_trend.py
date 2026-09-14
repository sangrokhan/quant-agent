"""Strategy: SMA(trend_window) directional gate with continuous Andean
Oscillator (bull-bear net pressure) sizing overlay + deadband,
leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Andean Oscillator (Alex Grover, 2022; per Google AI-overview cross-referencing
Alpaca/ProRealCode/TakeProfit -- web_search DDG backend failed for this
query, browser_exec fallback used) builds two one-directional ratchet
exponential envelopes around price/price^2 (upper envelope only moves down
toward price, lower envelope only moves up toward price, alpha=2/(length+1)):
    up1_t = max(close_t, open_t, up1_{t-1} - (up1_{t-1}-close_t)*alpha)
    up2_t = max(close_t^2, open_t^2, up2_{t-1} - (up2_{t-1}-close_t^2)*alpha)
    dn1_t = min(close_t, open_t, dn1_{t-1} + (close_t-dn1_{t-1})*alpha)
    dn2_t = min(close_t^2, open_t^2, dn2_{t-1} + (close_t^2-dn2_{t-1})*alpha)
    Bull = sqrt(|dn2 - dn1^2|)     (std-dev of price relative to lower env)
    Bear = sqrt(|up2 - up1^2|)     (std-dev of price relative to upper env)
This repo has exactly 1 prior Andean Oscillator entry (2026-09-05-016, a
binary EMA-signal-line crossover trigger). This iteration reframes the
indicator's own net pressure (Bull - Bear), normalized by price to make it
comparable across assets/time, as a CONTINUOUS SIZING dial: rolling
z-scored + tanh-squashed to [-1,1], used as a sizing multiplier within an
SMA(trend_window) uptrend gate, deadband to cut turnover, leverage_cap for
crypto. First Andean Oscillator continuous-sizing variant.

Source: https://www.prorealcode.com/prorealtime-indicators/andean-oscillator/
(formula + ProRealTime reference code), cross-checked against Google AI
overview citing Alpaca/TakeProfit for interpretation (Bull>Bear=buyers
dominate; crossovers=momentum shift).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
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


def _andean_bull_bear(close: pd.Series, open_: pd.Series, length: int):
    """Recursive ratchet-envelope Andean Oscillator Bull/Bear components.

    Implemented as an explicit Python loop since the recursion is
    inherently sequential (each step depends on the prior envelope value
    via a one-directional ratchet, not expressible as a plain pandas
    rolling/ewm op).
    """
    alpha = 2.0 / (length + 1)
    c = close.to_numpy(dtype=float)
    o = open_.to_numpy(dtype=float)
    n = len(c)
    up1 = np.empty(n)
    up2 = np.empty(n)
    dn1 = np.empty(n)
    dn2 = np.empty(n)
    up1[0] = c[0]
    up2[0] = c[0] * c[0]
    dn1[0] = c[0]
    dn2[0] = c[0] * c[0]
    for i in range(1, n):
        up1[i] = max(c[i], o[i], up1[i - 1] - (up1[i - 1] - c[i]) * alpha)
        up2[i] = max(
            c[i] * c[i], o[i] * o[i],
            up2[i - 1] - (up2[i - 1] - c[i] * c[i]) * alpha,
        )
        dn1[i] = min(c[i], o[i], dn1[i - 1] + (c[i] - dn1[i - 1]) * alpha)
        dn2[i] = min(
            c[i] * c[i], o[i] * o[i],
            dn2[i - 1] + (c[i] * c[i] - dn2[i - 1]) * alpha,
        )
        if dn1[i] == 0:
            dn1[i] = c[i]
        if dn2[i] == 0:
            dn2[i] = c[i] * c[i]

    bull = np.sqrt(np.abs(dn2 - dn1 * dn1))
    bear = np.sqrt(np.abs(up2 - up1 * up1))
    idx = close.index
    return pd.Series(bull, index=idx), pd.Series(bear, index=idx)


def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
    raw = raw_exposure.fillna(0.0).to_numpy()
    held = np.zeros_like(raw)
    current = 0.0
    for i, r in enumerate(raw):
        if abs(r - current) > deadband:
            current = r
        held[i] = current
    return pd.Series(held, index=raw_exposure.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    andean_length: int = 50,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Andean Oscillator net pressure (Bull - Bear), normalized by close price
    to make it scale-comparable, is rolling-z-scored over `zscore_window`
    bars and tanh-squashed to [-1,+1] before use as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"] if "open" in df.columns else close.shift(1).fillna(close)

    trend_long = close > close.rolling(trend_window).mean()
    bull, bear = _andean_bull_bear(close, open_, andean_length)
    net_pressure = (bull - bear) / close.replace(0.0, np.nan)

    roll_mean = net_pressure.rolling(zscore_window).mean()
    roll_std = net_pressure.rolling(zscore_window).std()
    zscore = (net_pressure - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    andean_length: int = 50,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        andean_length=andean_length,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
