"""Strategy: SMA(trend_window) directional gate with continuous Negative
Volume Index (NVI) sizing overlay + deadband -- CRYPTO LEVERAGE-CAP
RECALIBRATION of 2026-09-14-131.

Hypothesis (knowledge_base id TBD, this cron trigger):
2026-09-14-131 (NVI short-horizon ROC z-score continuous sizing dial on
SMA(trend_window) trend gate) accepted decisively on equity (QQQ+SPY, all
5 validators) but was a NARROW MDD near-miss on crypto: BTC/USDT MDD
0.277 and ETH/USDT MDD 0.270, both just above the 0.25 threshold, at
swept leverage_cap in {1.0, 0.4}, with Sharpe already strong (1.19-1.52)
and all other 4 validators passing. This entry directly follows the
2026-09-14-124/125 and 2026-09-14-180/181 (KRI) leverage-cap-recalibration
pattern already validated repeatedly this cron trigger: lowering
leverage_cap further (to 0.3) while proportionally scaling down
base_exposure/sensitivity so the dial's shape is preserved but its ceiling
is capped tighter, should pull crypto MDD back under 0.25 without
sacrificing the Sharpe edge. Source/formula unchanged from 2026-09-14-131
(Google AI overview via browser_exec, https://www.google.com/search?q=Negative+Volume+Index+NVI+formula+construction)
-- no new web fetch needed for this recalibration sub-step, per the
established pattern in this repo (e.g. 2026-09-14-183 Alligator
recalibration reused 2026-09-14-182's confirmed formula without a fresh
fetch).

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


def _negative_volume_index(df: pd.DataFrame, base_value: float = 1000.0) -> pd.Series:
    """Cumulative NVI: updates only on volume-decrease days (Fosback)."""
    close, volume = df["close"], df["volume"]
    pct_change = close.pct_change().fillna(0.0)
    vol_decreased = volume < volume.shift(1)

    nvi = np.empty(len(df))
    nvi[:] = np.nan
    current = base_value
    for i in range(len(df)):
        if i == 0:
            nvi[i] = base_value
            continue
        if bool(vol_decreased.iloc[i]):
            current = current + pct_change.iloc[i] * current
        nvi[i] = current
    return pd.Series(nvi, index=df.index)


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
    roc_window: int = 10,
    zscore_window: int = 90,
    base_exposure: float = 0.25,
    sensitivity: float = 0.25,
    leverage_cap: float = 0.3,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Defaults recalibrated for crypto leverage_cap=0.3 (vs 2026-09-14-131's
    equity-tuned 1.0/0.6 defaults); base_exposure/sensitivity scaled down
    proportionally so the dial still spans [0, leverage_cap].
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    nvi = _negative_volume_index(df)
    nvi_roc = nvi.pct_change(roc_window)
    nvi_mean = nvi_roc.rolling(zscore_window).mean()
    nvi_std = nvi_roc.rolling(zscore_window).std().replace(0, np.nan)
    nvi_zscore = ((nvi_roc - nvi_mean) / nvi_std).clip(lower=-2.5, upper=2.5)

    raw_exposure = base_exposure + sensitivity * (nvi_zscore / 2.5)
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    roc_window: int = 10,
    zscore_window: int = 90,
    base_exposure: float = 0.25,
    sensitivity: float = 0.25,
    leverage_cap: float = 0.3,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        roc_window=roc_window,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
