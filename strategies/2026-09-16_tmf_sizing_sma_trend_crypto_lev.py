"""Strategy: SMA(trend_window) directional gate with continuous Twiggs
Money Flow (true-range-based, EMA-smoothed) sizing overlay + deadband --
CRYPTO LEVERAGE-CAP RECALIBRATION of 2026-09-14-123.

Hypothesis (knowledge_base id TBD, this cron trigger):
2026-09-14-123 (Twiggs Money Flow continuous sizing dial on
SMA(trend_window) trend gate) accepted decisively on equity (QQQ+SPY, all
5 validators) but was rejected on crypto with an MDD-only miss: BTC/USDT
MDD 31.4% against the 25% threshold, with Sharpe 1.514 (pass), TC-survival
1.364 (pass), and walk-forward 1.0 (pass) -- all other 4 validators
already passing at leverage_cap left at the equity default 1.0. This
entry applies this repo's established leverage-cap-aware retune pattern:
cut leverage_cap to 0.3, scale down base_exposure and deadband
proportionally so the dial's shape (TMF sizing signal, already natively
bounded ~[-1,1]) is preserved but its exposure ceiling is capped tightly
enough for crypto's higher realized vol to keep drawdown under 25%.
Formula/source unchanged from 2026-09-14-123 (Colin Twiggs;
incrediblecharts.com, read via browser_exec) -- no new external fetch
needed for this crypto-only recalibration sub-step.

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


def _twiggs_money_flow(df: pd.DataFrame, window: int = 21) -> pd.Series:
    """TMF = EMA(ADV, window) / EMA(Volume, window). Naturally bounded
    ~[-1, 1] by construction."""
    high, low, close, volume = df["high"], df["low"], df["close"], df["volume"]
    prev_close = close.shift(1)
    tr_high = pd.concat([high, prev_close], axis=1).max(axis=1)
    tr_low = pd.concat([low, prev_close], axis=1).min(axis=1)
    tr_range = (tr_high - tr_low).replace(0, np.nan)

    adv = ((close - tr_low) - (tr_high - close)) / tr_range * volume
    tmf = adv.ewm(span=window, adjust=False).mean() / volume.ewm(span=window, adjust=False).mean()
    return tmf.clip(lower=-1.0, upper=1.0)


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
    tmf_window: int = 21,
    base_exposure: float = 0.15,
    sensitivity: float = 0.5,
    leverage_cap: float = 0.3,
    deadband: float = 0.10,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    tmf = _twiggs_money_flow(df, window=tmf_window)

    raw_exposure = base_exposure + sensitivity * tmf * leverage_cap
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    tmf_window: int = 21,
    base_exposure: float = 0.15,
    sensitivity: float = 0.5,
    leverage_cap: float = 0.3,
    deadband: float = 0.10,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        tmf_window=tmf_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
