"""Strategy: Volatility-adjusted (return-to-volatility ratio) absolute
momentum trend entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-065):
Per Alpha in Academia's "Volatility-Adjusted ETF Momentum" post (building
on Raju's "Shades of Momentum" SSRN working paper), traditional momentum
rewards raw return without penalizing risk; volatility-adjusted momentum
instead ranks/signals on the RETURN-TO-VOLATILITY RATIO over a fixed
lookback window (trailing return divided by realized volatility over the
same window, annualized, zero-cash-rate assumption -- explicitly NOT an
excess-return Sharpe ratio) rather than raw return alone. The source's
cross-sectional ETF-ranking design is adapted here to a single-asset
ABSOLUTE signal (since this repo's grid tester operates one symbol at a
time, not a cross-sectional universe): go long when the trailing
lookback_window-day return-to-volatility ratio exceeds a positive
ratio_threshold (the asset is compounding gains smoothly, not just
noisily rising), exit when the ratio drops back below an exit_threshold
(momentum quality deteriorating) or a max_hold_days time-stop.

This is mechanically distinct from every prior TSMOM/dual-momentum
strategy already tested in this repo (2026-09-03-012 TSMOM uses RAW
12-month return only, no volatility division; 2026-09-04's dual momentum
rotation and GEM variants rank/gate on raw return or a raw-return-vs-SMA
check, never a return/vol RATIO) and from all vol-TARGETING position-
sizing strategies (e.g. BTC momentum vol-target, 2026-09-03, which SCALES
position size by inverse-vol but still gates entry on raw return sign, not
a return/vol ratio threshold).

Source: https://www.alphainacademia.com/volatility-adjusted-etf-momentum/

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def generate_signals(
    price_df: pd.DataFrame,
    lookback_window: int = 126,
    ratio_threshold: float = 1.0,
    exit_threshold: float = 0.0,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    daily_ret = close.pct_change()
    trailing_ret = close.pct_change(lookback_window)
    realized_vol = daily_ret.rolling(lookback_window).std() * (252 ** 0.5)
    annualized_trailing_ret = (1 + trailing_ret).pow(252.0 / lookback_window) - 1

    vol_adj_momentum = (annualized_trailing_ret / realized_vol.replace(0, np.nan)).fillna(-np.inf)

    entry = vol_adj_momentum >= ratio_threshold
    exit_signal = vol_adj_momentum < exit_threshold

    entry_arr = entry.to_numpy(dtype=bool)
    exit_arr = exit_signal.to_numpy(dtype=bool)

    position = np.zeros(n, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_arr[i]) or held >= max_hold_days:
                in_position = False
                position[i] = 0
                continue
            position[i] = 1
        else:
            if bool(entry_arr[i]):
                in_position = True
                entry_idx = i
                position[i] = 1
            else:
                position[i] = 0

    return pd.Series(position, index=close.index, dtype=int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    # Shift position by 1 day: yesterday's signal determines today's return
    # exposure (avoid look-ahead bias -- can't trade on today's own close).
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
