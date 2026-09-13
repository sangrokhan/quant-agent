"""Strategy: SMA(trend_window) directional gate with continuous Intraday
Momentum Index (IMI) sizing overlay + deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id 2026-09-14-100):
Intraday Momentum Index (Tushar Chande; formula per DuckDuckGo HTML SERP
results from ta-lib.org, blinkx.in, alphasquawk.com, figurebetter.com --
all consistent): an RSI-like 0-100 oscillator built from each bar's own
open-to-close body move rather than close-to-close changes -- over a
rolling window, it ratios cumulative up-body magnitude against total
up+down body magnitude: IMI = 100 * sum(up_body) / (sum(up_body) +
sum(down_body)), where up_body = max(close-open, 0) and down_body =
max(open-close, 0) per bar.

This repo has one prior IMI entry (2026-09-05-071), a binary
oversold-recovery mean-reversion ENTRY trigger, accepted SPY-only (QQQ
near-miss, crypto decisively rejected). This iteration instead uses IMI as
a CONTINUOUS SIZING dial (rescaled around its 50-midpoint) within an
SMA(trend_window) uptrend gate, following the same reframing pattern that
rescued/refined VZO/ADX/DMI-diff/CHOP/Vortex/TSI/RMI/SMI/BOP earlier this
cron trigger -- testing whether the sizing-dial construction can extend
IMI's edge to QQQ as well (its near-miss in the binary framing hints there
may be real signal there that a continuous dial captures better).

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


def _imi(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """IMI = 100 * sum(up_body, window) / sum(up_body+down_body, window),
    bounded [0, 100] by construction (ratio of nonnegative sums)."""
    close = df["close"]
    open_ = df["open"]

    body = close - open_
    up_body = body.clip(lower=0.0)
    down_body = (-body).clip(lower=0.0)

    sum_up = up_body.rolling(window).sum()
    sum_down = down_body.rolling(window).sum()
    denom = (sum_up + sum_down).replace(0, np.nan)

    imi = 100.0 * sum_up / denom
    return imi.clip(lower=0.0, upper=100.0)


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
    imi_window: int = 14,
    base_exposure: float = 0.5,
    imi_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    imi = _imi(df, window=imi_window)
    imi_norm = (imi - 50.0) / 50.0  # rescale to roughly [-1, 1] around midpoint

    raw_exposure = base_exposure + imi_sensitivity * imi_norm
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    imi_window: int = 14,
    base_exposure: float = 0.5,
    imi_sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        imi_window=imi_window,
        base_exposure=base_exposure,
        imi_sensitivity=imi_sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
