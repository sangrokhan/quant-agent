"""Strategy: SMA(trend_window) directional gate with continuous Random Walk
Index (RWI) diff sizing overlay + deadband -- CRYPTO LEVERAGE-CAP
RECALIBRATION of 2026-09-14-104.

Hypothesis (knowledge_base id TBD, this cron trigger):
2026-09-14-104 (RWI signed-diff tanh-squashed continuous sizing dial on
SMA(trend_window) trend gate) accepted decisively on equity (QQQ+SPY, all
5 validators) but was DECISIVELY rejected on crypto: BTC/USDT MDD 37.99%
against the 25% threshold, at swept rwi_sensitivity in {0.4,0.6,0.8} and
deadband in {0.15,0.2,0.25} with leverage_cap left at the equity default
1.0. This entry applies this repo's now-repeatedly-validated
leverage-cap-aware retune pattern (e.g. TSI 2026-09-16-063, RMI
2026-09-16-064, SMI 2026-09-16-065, BOP 2026-09-16-066, IMI 2026-09-16-067,
NVI 2026-09-14 crypto-lev variant): cut leverage_cap sharply (to 0.3),
scale down base_exposure proportionally, and scale down deadband
proportionally (0.25 -> 0.08) so the dial's *shape* (tanh(rwi_diff) sizing
signal) is preserved but its exposure ceiling is capped tightly enough for
crypto's higher realized vol to keep drawdown under 25% while retaining
the dial's strong crypto Sharpe (1.52 in the original grid) and near-zero
param-sensitivity (0.013). Formula/source unchanged from 2026-09-14-104
(RWI_high/RWI_low ATR*sqrt(n) normalized displacement vs random-walk
expectation, Michael Poulos; DuckDuckGo HTML SERP linnsoft.com,
strike.money, stockmaniacs.net, tradingsim.com) -- no new external fetch
needed for this crypto-only recalibration sub-step, per the established
pattern in this repo of reusing a confirmed formula for a leverage-cap
retune.

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


def _true_range(df: pd.DataFrame) -> pd.Series:
    high = df["high"]
    low = df["low"]
    prior_close = df["close"].shift(1)
    return pd.concat(
        [high - low, (high - prior_close).abs(), (low - prior_close).abs()],
        axis=1,
    ).max(axis=1)


def _rwi_diff(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """tanh(RWI_high - RWI_low), squashed to bounded [-1, 1]."""
    high = df["high"]
    low = df["low"]

    tr = _true_range(df)
    atr = tr.rolling(window).mean()
    denom = (atr * np.sqrt(window)).replace(0, np.nan)

    rwi_high = (high - low.shift(window)) / denom
    rwi_low = (high.shift(window) - low) / denom

    rwi_diff = rwi_high - rwi_low
    return np.tanh(rwi_diff)


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
    rwi_window: int = 14,
    base_exposure: float = 0.15,
    rwi_sensitivity: float = 0.65,
    leverage_cap: float = 0.3,
    deadband: float = 0.08,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    rwi_signal = _rwi_diff(df, window=rwi_window)  # already tanh-squashed to [-1, 1]

    raw_exposure = base_exposure + rwi_sensitivity * rwi_signal * leverage_cap
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    rwi_window: int = 14,
    base_exposure: float = 0.15,
    rwi_sensitivity: float = 0.65,
    leverage_cap: float = 0.3,
    deadband: float = 0.08,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        rwi_window=rwi_window,
        base_exposure=base_exposure,
        rwi_sensitivity=rwi_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
