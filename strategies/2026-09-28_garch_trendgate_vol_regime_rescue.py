"""Strategy: plain symmetric GARCH(1,1) volatility regime gate + SMA trend
filter -- direct rescue of this repo's own prior near-miss (2026-09-07-015).

This same cron trigger already rescued TWO other GARCH-family pure vol-gate
entries (GJR-GARCH 2026-09-28-022, EGARCH 2026-09-28-024) with the
identical fix: AND the calm-volatility gate with a plain
close > SMA(trend_window) trend filter, since a pure vol-only regime gate
has no directional awareness and can stay long through a calm-but-
declining regime, inflating drawdown/hurting Sharpe. This iteration applies
that same fix to the plain symmetric GARCH(1,1) gate
(strategies/2026-09-07_garch_vol_regime_gate.py, unmodified, imported
directly) -- closing out the repo's full symmetric/GJR/EGARCH GARCH-family
rescue sweep this cron trigger.

No new external source -- internal debugging/rescue of an already-logged
near-miss, reusing the prior file's exact GARCH(1,1) MLE-fit code.

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
_garch_mod = importlib.import_module("2026-09-07_garch_vol_regime_gate")


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    lookback: int = 250,
    refit_every: int = 21,
    vol_threshold: float = 0.25,
    trend_window: int = 150,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a {0,1}*leverage_cap long/flat position series.

    Reuses the prior file's unmodified ``generate_signals`` (pure GARCH(1,1)
    vol-regime gate) and ANDs it with a ``close > SMA(trend_window)`` trend
    filter -- the same fix pattern that rescued this cron trigger's
    GJR-GARCH and EGARCH entries. ``trend_window=0`` disables the filter.
    """
    df = _prep(price_df)
    close = df["close"]

    vol_gate = _garch_mod.generate_signals(
        df, lookback=lookback, refit_every=refit_every, vol_threshold=vol_threshold
    )
    calm = vol_gate.astype(bool)

    if trend_window and trend_window > 0:
        sma = close.rolling(trend_window).mean()
        trend_ok = (close > sma).fillna(False)
        calm = calm & trend_ok

    return calm.astype(float) * leverage_cap


def generate_returns(
    price_df: pd.DataFrame,
    lookback: int = 250,
    refit_every: int = 21,
    vol_threshold: float = 0.25,
    trend_window: int = 150,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return the daily strategy return series (no transaction costs)."""
    df = _prep(price_df)
    pos = generate_signals(
        df,
        lookback=lookback,
        refit_every=refit_every,
        vol_threshold=vol_threshold,
        trend_window=trend_window,
        leverage_cap=leverage_cap,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0.0)
    return strat_ret
