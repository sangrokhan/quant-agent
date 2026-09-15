"""Strategy: SMA(trend_window) directional gate with continuous
Bulk-Volume-Classification (BVC) order-flow imbalance sizing overlay +
deadband, leverage-cap-aware for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per quantmedia.io's VPIN explainer (already visited/logged in this repo's
ledger from id 2026-09-09-024; formula re-used unchanged, no new fetch
this iteration) and the underlying Easley/Lopez de Prado/O'Hara VPIN
literature, Bulk Volume Classification (BVC) infers buy- vs sell-initiated
volume from the standardized price change via a normal CDF:
    buy_frac_t = Phi(return_t / sigma_t)
    signed_imbalance_t = 2*buy_frac_t - 1   (naturally bounded [-1, 1])
    weighted_imbalance = sum(volume*signed_imbalance) / sum(volume) over a
        trailing window (the daily-bar analogue of a BVC "bucket average")

This repo's existing BVC entry
(strategies/2026-09-09_bvc_orderflow_imbalance_momentum.py, id
2026-09-09-024) used weighted_imbalance as a binary entry/exit hysteresis
threshold and was a NEAR-MISS (QQQ Sharpe 0.953, close to the 1.0
threshold) on equity, decisively rejected on crypto; a vol-gated follow-up
(2026-09-09-025) made it worse. Since weighted_imbalance is ALREADY
naturally bounded [-1,1] (no z-score/tanh squashing needed, unlike most
sizing dials in this repo), this iteration reframes it directly as a
CONTINUOUS SIZING dial within an SMA(trend_window) uptrend gate -- testing
whether the near-miss binary threshold was discarding useful information
in the continuum, the same rationale that has rescued/broadened several
other near-miss or rejected binary indicators this cron trigger. First
BVC-as-continuous-sizing-dial strategy in this repo.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

try:
    from scipy.stats import norm

    def _phi(x: pd.Series) -> pd.Series:
        return pd.Series(norm.cdf(x.values), index=x.index)
except Exception:  # pragma: no cover - fallback if scipy unavailable
    def _phi(x: pd.Series) -> pd.Series:
        return 1.0 / (1.0 + np.exp(-1.702 * x))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _weighted_imbalance(df: pd.DataFrame, sigma_window: int, imbalance_window: int) -> pd.Series:
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=df.index)
    ret = close.pct_change()
    sigma = ret.rolling(sigma_window).std()
    sigma_safe = sigma.replace(0.0, np.nan)
    z = (ret / sigma_safe).clip(-5, 5).fillna(0.0)
    buy_frac = _phi(z)
    signed_imbalance = 2 * buy_frac - 1  # in [-1, 1]

    num = (volume * signed_imbalance).rolling(imbalance_window).sum()
    den = volume.rolling(imbalance_window).sum().replace(0.0, np.nan)
    weighted_imbalance = (num / den).fillna(0.0)
    return weighted_imbalance


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
    sigma_window: int = 20,
    imbalance_window: int = 10,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    exposure = clip(base_exposure + sensitivity*weighted_imbalance, 0, cap)
    (weighted_imbalance already naturally bounded [-1,1], no z-score/tanh
    needed), gated to 0 whenever close is below its SMA(trend_window).
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    weighted_imbalance = _weighted_imbalance(df, sigma_window, imbalance_window)

    raw_exposure = base_exposure + sensitivity * weighted_imbalance
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    sigma_window: int = 20,
    imbalance_window: int = 10,
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
        sigma_window=sigma_window,
        imbalance_window=imbalance_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
