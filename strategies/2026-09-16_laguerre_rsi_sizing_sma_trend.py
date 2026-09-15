"""Strategy: SMA(trend_window) directional gate with continuous Laguerre RSI
(Ehlers) sizing overlay + deadband, leverage-cap-aware for crypto from the
start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Direct fix attempt for prior id 2026-09-16-138 (Laguerre RSI (Ehlers) 4-stage
Laguerre-filtered oscillator, bounded [0,1], oversold-recovery-to-overbought-
exhaustion binary state-machine entry/exit: accepted EQUITY ONLY (QQQ+SPY),
crypto not validated broadly at that config -- BTC 1/3 vol regimes, ETH
0/3). Source unchanged: https://www.quantifiedstrategies.com/laguerre-rsi/
(already visited/logged this cron trigger's own ledger).

LRSI is already naturally bounded in [0,1] by construction (a ratio of
positive to total Laguerre-filter-stage differences) -- no z-score/tanh
needed, the same "already-bounded -> use directly as a sizing dial" pattern
already validated for BVC and this cron trigger's Ehlers Reversion Index.
Rather than a binary state-machine hold, this reframes LRSI as a CONTINUOUS
SIZING dial: exposure = base_exposure + sensitivity*(LRSI - 0.5)*2 (centered
so LRSI=0.5 is neutral, LRSI=1 is maximally bullish, LRSI=0 is maximally
bearish/zero exposure), inside an SMA(trend_window) uptrend gate with a
deadband, leverage-cap-aware for crypto. First Laguerre-RSI-as-continuous-
sizing-dial strategy in this repo.

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


def _laguerre_rsi(price: pd.Series, gamma: float = 0.5) -> pd.Series:
    """Ehlers Laguerre RSI: smooth 0..1 oscillator via a 4-stage Laguerre filter.
    Unchanged formula from strategies/2026-09-16_laguerre_rsi_oversold_recovery.py."""
    p = price.to_numpy(dtype=float)
    n = len(p)
    l0 = np.zeros(n)
    l1 = np.zeros(n)
    l2 = np.zeros(n)
    l3 = np.zeros(n)
    lrsi = np.full(n, 0.5)

    for i in range(n):
        if i == 0:
            l0[i] = p[i]
            l1[i] = p[i]
            l2[i] = p[i]
            l3[i] = p[i]
            continue
        l0[i] = (1 - gamma) * p[i] + gamma * l0[i - 1]
        l1[i] = -gamma * l0[i] + l0[i - 1] + gamma * l1[i - 1]
        l2[i] = -gamma * l1[i] + l1[i - 1] + gamma * l2[i - 1]
        l3[i] = -gamma * l2[i] + l2[i - 1] + gamma * l3[i - 1]

        cu = 0.0
        cd = 0.0
        for d in (l0[i] - l1[i], l1[i] - l2[i], l2[i] - l3[i]):
            if d >= 0:
                cu += d
            else:
                cd += -d
        denom = cu + cd
        lrsi[i] = cu / denom if denom > 1e-12 else 0.5

    return pd.Series(lrsi, index=price.index)


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
    gamma: float = 0.5,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    LRSI is already bounded [0,1] -- centered as (LRSI-0.5)*2 to [-1,1]
    before being used as a sizing dial: exposure = clip(base_exposure +
    sensitivity*dial, 0, cap), gated to 0 whenever close is below its
    SMA(trend_window).
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    lrsi = _laguerre_rsi(close, gamma=gamma)
    dial = (lrsi - 0.5) * 2.0

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    gamma: float = 0.5,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        gamma=gamma,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
