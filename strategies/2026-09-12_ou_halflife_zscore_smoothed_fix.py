"""Strategy: OU half-life-gated Z-score mean reversion, SMOOTHED-Z fix attempt.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Direct fix attempt for near-miss 2026-09-07-012 (OU half-life-gated Z-score
mean reversion): that strategy passed Sharpe/MDD/TC/walk-forward on SPY at
entry_z=1.5, lookback=40, but FAILED parameter sensitivity (relative_std
0.59 > 0.5) -- entry_z=1.5 was a fragile local optimum with Sharpe
collapsing ~68% one notch off-peak on either side of the raw single-bar
z-score, a classic overfit signature of trading a noisy instantaneous
statistic.

This iteration's fix: apply a short rolling-mean SMOOTHING to the z-score
itself (z_smooth = z.rolling(smooth_window).mean()) before thresholding,
on the theory (standard OU/mean-reversion-signal-processing practice) that
smoothing a noisy mean-reversion signal trades a small amount of timing
precision for a flatter, less overfit-prone parameter response surface --
i.e. this directly targets the specific rejection reason (param-sensitivity
overfit spike) rather than re-testing the identical unsmoothed construction.
Same underlying OU AR(1)-fit / half-life-gate mechanism as 2026-09-07-012
(unchanged), only the entry/exit trigger series is smoothed.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
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
    lookback: int = 60,
    entry_z: float = 1.5,
    exit_z: float = 0.0,
    min_halflife: float = 5.0,
    max_halflife: float = 30.0,
    max_hold_days: int = 20,
    smooth_window: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    X = np.log(close.clip(lower=1e-9))
    dX = X.diff()
    X_lag = X.shift(1)

    roll_cov = X_lag.rolling(lookback).cov(dX)
    roll_var = X_lag.rolling(lookback).var()
    b = roll_cov / roll_var
    a = dX.rolling(lookback).mean() - b * X_lag.rolling(lookback).mean()

    pred = a + b * X_lag
    resid = dX - pred
    sigma_resid = resid.rolling(lookback).std()

    with np.errstate(invalid="ignore", divide="ignore"):
        theta = -np.log1p(b)
        half_life = np.log(2) / theta
        mu = -a / b
        sigma_eq = sigma_resid * np.sqrt(1.0 / (2.0 * theta))
        z_raw = (X - mu) / sigma_eq

    z = z_raw.rolling(smooth_window, min_periods=1).mean()

    tradable = (
        (b < 0)
        & (half_life >= min_halflife)
        & (half_life <= max_halflife)
        & theta.replace([np.inf, -np.inf], np.nan).notna()
        & z.notna()
    )
    entry = tradable & (z < -entry_z)
    exit_meanrev = z >= -exit_z

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            exit_hit = bool(exit_meanrev.iloc[i]) if not pd.isna(exit_meanrev.iloc[i]) else True
            regime_break = not bool(tradable.iloc[i]) if not pd.isna(tradable.iloc[i]) else True
            if exit_hit or regime_break or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            entry_hit = bool(entry.iloc[i]) if not pd.isna(entry.iloc[i]) else False
            if entry_hit:
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
