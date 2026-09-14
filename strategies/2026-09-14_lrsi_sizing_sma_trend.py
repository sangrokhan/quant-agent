"""Strategy: SMA(trend_window) directional gate with continuous Ehlers
Laguerre RSI (LRSI) sizing overlay + deadband, leverage-cap-aware for
crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Ehlers Laguerre RSI (4-stage recursive Laguerre filter L0-L3, RSI-style
logic applied to the filtered levels, naturally bounded [0,1]) per
https://www.quantifiedstrategies.com/laguerre-rsi/ (visited this
iteration): "Using Zero Line (0.5) as Momentum Bias: When the Laguerre RSI
stays above 0.5, momentum is bullish. Below 0.5 indicates bearish
momentum." Repo has 4 prior LRSI entries, ALL using it as a discrete
mean-reversion threshold trigger (2026-09-05-053, rejected), a standalone
binary >0.5/<=0.5 regime filter (2026-09-06-110), a variant (Adaptive
Laguerre Filter, 2026-09-05-058), or an Ehlers Continuation Index derivative
(2026-09-12-173) -- none use LRSI's own [0,1] bounded value as a CONTINUOUS
sizing dial. Since LRSI is already naturally normalized [0,1], this
iteration directly rescales it to [-1,+1] (centered at its own 0.5 zero
line, per the source's own momentum-bias framing) and uses that as a
continuous sizing dial within an SMA(trend_window) uptrend gate -- the same
"naturally-bounded oscillator -> direct rescale -> sizing dial" pattern
already used successfully for DVO, EBSW, VoRSI, and the Elegant Oscillator
earlier this cron trigger. First LRSI continuous-sizing variant.

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


def _laguerre_rsi(close: pd.Series, gamma: float) -> pd.Series:
    """Ehlers Laguerre RSI: 4-stage recursive Laguerre filter (L0..L3),
    then RSI-style logic (CU/CD accumulation of up/down differences between
    consecutive stages) yielding a naturally [0,1]-bounded oscillator."""
    c = close.to_numpy(dtype=float)
    n = len(c)
    l0 = np.zeros(n)
    l1 = np.zeros(n)
    l2 = np.zeros(n)
    l3 = np.zeros(n)
    lrsi = np.zeros(n)

    for i in range(n):
        if i == 0:
            l0[i] = l1[i] = l2[i] = l3[i] = c[i]
            lrsi[i] = 0.5
            continue
        l0[i] = (1 - gamma) * c[i] + gamma * l0[i - 1]
        l1[i] = -gamma * l0[i] + l0[i - 1] + gamma * l1[i - 1]
        l2[i] = -gamma * l1[i] + l1[i - 1] + gamma * l2[i - 1]
        l3[i] = -gamma * l2[i] + l2[i - 1] + gamma * l3[i - 1]

        cu = 0.0
        cd = 0.0
        if l0[i] >= l1[i]:
            cu += l0[i] - l1[i]
        else:
            cd += l1[i] - l0[i]
        if l1[i] >= l2[i]:
            cu += l1[i] - l2[i]
        else:
            cd += l2[i] - l1[i]
        if l2[i] >= l3[i]:
            cu += l2[i] - l3[i]
        else:
            cd += l3[i] - l2[i]

        denom = cu + cd
        lrsi[i] = (cu / denom) if denom != 0 else lrsi[i - 1]

    return pd.Series(lrsi, index=close.index)


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

    LRSI (naturally [0,1]) is directly rescaled to [-1,+1] around its own
    0.5 zero line, then used as a sizing dial within an SMA(trend_window)
    uptrend gate.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    lrsi = _laguerre_rsi(close, gamma)
    dial = (lrsi - 0.5) * 2.0  # rescale [0,1] -> [-1,+1]

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
