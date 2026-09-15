"""Strategy: SMA(trend_window) directional gate with continuous Elder-Ray
Net Power (ATR-normalized Bull Power minus Bear Power) sizing overlay +
deadband -- CRYPTO LEVERAGE-CAP RECALIBRATION of 2026-09-14-121.

Hypothesis (knowledge_base id TBD, this cron trigger):
2026-09-14-121 (Elder-Ray ATR-normalized net power continuous sizing dial
on SMA(trend_window) trend gate) accepted decisively on equity (QQQ+SPY,
all 5 validators, first Elder-Ray accept in this repo after 8 prior
binary-trigger rejections) but was rejected on crypto with an MDD-only
miss: BTC/USDT MDD 37.7% against the 25% threshold, with Sharpe 1.497
(pass), TC-survival 0.871 (pass), walk-forward 1.0 (pass), and
param-sensitivity 0.014 (pass) -- all other 4 validators already passing
at leverage_cap left at the equity default 1.0. This entry applies this
repo's established leverage-cap-aware retune pattern: cut leverage_cap to
0.3, scale down base_exposure and deadband proportionally so the dial's
shape (ATR-normalized Elder-Ray net-power sizing signal) is preserved but
its exposure ceiling is capped tightly enough for crypto's higher realized
vol to keep drawdown under 25%. Formula/source unchanged from
2026-09-14-121 (Dr. Alexander Elder, 1989; investopedia.com/terms/e/
elderray.asp, read via browser_exec) -- no new external fetch needed for
this crypto-only recalibration sub-step.

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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def _elder_ray_net_power(df: pd.DataFrame, ema_window: int, atr_window: int) -> pd.Series:
    """ATR-normalized Elder-Ray net power: (BullPower - BearPower) / ATR."""
    ema = df["close"].ewm(span=ema_window, adjust=False).mean()
    bull_power = df["high"] - ema
    bear_power = df["low"] - ema
    atr = _atr(df, atr_window)
    net_power = (bull_power - bear_power) / atr.replace(0, np.nan)
    return net_power


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
    ema_window: int = 13,
    atr_window: int = 14,
    net_power_reference: float = 2.0,
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
    net_power = _elder_ray_net_power(df, ema_window=ema_window, atr_window=atr_window)
    net_power_norm = (net_power / net_power_reference).clip(lower=-1.5, upper=1.5)

    raw_exposure = base_exposure + sensitivity * net_power_norm * leverage_cap
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    ema_window: int = 13,
    atr_window: int = 14,
    net_power_reference: float = 2.0,
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
        ema_window=ema_window,
        atr_window=atr_window,
        net_power_reference=net_power_reference,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
