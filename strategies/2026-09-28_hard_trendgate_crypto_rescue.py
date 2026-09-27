"""Strategy: HAR-D (overnight/intraday decomposed HAR) volatility gate +
SMA trend filter -- crypto rescue.

This iteration completes this cron trigger's GARCH/HAR-family vol-gate
rescue sweep: HAR-D (strategies/2026-09-20_har_d_overnight_intraday_vol_gate.py,
id 2026-09-20-100) was already ACCEPTED on equity (SPY/QQQ) but REJECTED on
its crypto leg. This cron trigger already demonstrated (GJR-GARCH
2026-09-28-022, EGARCH 2026-09-28-024, plain GARCH 2026-09-28-025) that
pure calm-volatility-regime gates need an explicit `close > SMA(trend_window)`
directional filter to control drawdown -- HAR-D's crypto rejection notes
were not re-examined with this specific fix. This iteration applies the
identical trend-filter AND-gate to HAR-D's unmodified forecast code
(imported directly from the prior file) and retunes crypto-appropriate
vol_threshold/leverage_cap, following this repo's now-established pattern.

No new external source -- internal rescue reusing the prior HAR-D model's
exact OLS-based overnight/intraday-decomposed forecast code.

Interface contract (see validation/validators.py and validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import sys
import os
import importlib

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_hard_mod = importlib.import_module("2026-09-20_har_d_overnight_intraday_vol_gate")


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    vol_threshold: float = 0.20,
    min_train: int = 250,
    refit_every: int = 20,
    trend_window: int = 100,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a {0,1}*leverage_cap long/flat position series.

    Reuses the prior file's unmodified ``generate_signals`` (pure HAR-D
    vol-regime gate) and ANDs it with a ``close > SMA(trend_window)`` trend
    filter -- the same fix pattern that rescued this cron trigger's
    GJR-GARCH/EGARCH/plain-GARCH entries. ``trend_window=0`` disables the
    filter (reproduces the original behavior for direct comparison).
    """
    df = _prep(price_df)
    close = df["close"]

    vol_gate = _hard_mod.generate_signals(
        df, vol_threshold=vol_threshold, min_train=min_train, refit_every=refit_every
    )
    calm = vol_gate.astype(bool)

    if trend_window and trend_window > 0:
        sma = close.rolling(trend_window).mean()
        trend_ok = (close > sma).fillna(False)
        calm = calm & trend_ok

    return calm.astype(float) * leverage_cap


def generate_returns(
    price_df: pd.DataFrame,
    vol_threshold: float = 0.20,
    min_train: int = 250,
    refit_every: int = 20,
    trend_window: int = 100,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return the daily strategy return series (no transaction costs)."""
    df = _prep(price_df)
    pos = generate_signals(
        df,
        vol_threshold=vol_threshold,
        min_train=min_train,
        refit_every=refit_every,
        trend_window=trend_window,
        leverage_cap=leverage_cap,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0.0)
    return strat_ret
