"""Strategy: EGARCH(1,1) asymmetric-volatility regime gate + SMA trend filter.

Rescue/retest of this repo's own prior rejected entry (2026-09-20-095,
strategies/2026-09-20_egarch_asymmetric_vol_regime_gate.py): that entry
tested EGARCH's log-conditional-variance leverage-effect asymmetry
(Nelson 1991) as a PURE volatility-regime gate (long while forecast vol
<= threshold, flat otherwise) and was rejected -- best full-sample Sharpe
0.809 on QQQ, "no better than the prior plain-GARCH near-miss".

This same cron trigger's GJR-GARCH entry (2026-09-28-022, id this trigger)
found the identical root cause for a near-identical pure-vol-gate framing:
a calm-volatility-only gate has no information about price DIRECTION, so it
happily stays long through a calm-but-declining regime (e.g. a slow
grinding bear market with low realized vol), which both caps upside and
inflates drawdown enough to fail the Sharpe/MDD thresholds. Adding a plain
`close > SMA(trend_window)` AND-gate fixed GJR-GARCH decisively (QQQ Sharpe
0.923->1.397, full-universe accept). This iteration applies the identical
fix to EGARCH's own already-implemented log-variance leverage-effect
model, reusing its existing MLE-fit function unmodified (imported from the
prior file, not reimplemented) and adding only the trend-filter AND-gate on
top -- isolating whether the SAME fix that rescued GJR-GARCH also rescues
EGARCH, or whether EGARCH's specific asymmetry construction has some other
issue GJR-GARCH's construction does not share.

Interface contract (see validation/validators.py and validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import sys
import os

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib

_egarch_mod = importlib.import_module("2026-09-20_egarch_asymmetric_vol_regime_gate")


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

    Reuses the prior file's unmodified ``generate_signals`` (pure EGARCH
    vol-regime gate) and ANDs it with a ``close > SMA(trend_window)`` trend
    filter -- the exact fix pattern that rescued this cron trigger's
    GJR-GARCH entry. ``trend_window=0`` disables the filter (reproduces the
    original rejected pure-vol-gate behavior for direct comparison).
    """
    df = _prep(price_df)
    close = df["close"]

    vol_gate = _egarch_mod.generate_signals(
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
