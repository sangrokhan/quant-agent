"""Strategy: R-squared linear regression trend-quality gate + slope-direction
trend following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-004):
The R-squared (coefficient of determination) of a rolling linear regression
of close price against time measures how well price fits a straight line
over the lookback window -- i.e. "trend quality" (near 1.0 = clean, orderly
trend; near 0 = noisy/choppy/directionless). Per multiple corroborating
sources found via Google search (AlgoKing's Linear Regression FAQ snippet:
"Use R-Squared as a trend quality filter. When R-squared is high (>0.8),
price is moving in a clear trend -- trust [the regression slope
direction]"; LuxAlgo's R-squared Trend Fit concept; FMZ's multi-layer
statistical regression strategy using an R-squared threshold), only trade
the regression slope's direction when R-squared exceeds a threshold (0.8
default), flat otherwise. This should filter out the whipsaw-prone choppy
regimes that hurt many of this repo's unconditional trend-following
strategies while keeping exposure during genuinely clean trending periods.

Distinct from the already-tried linear-regression-slope mean-reversion
strategy (2026-09-04-058, negative-slope contrarian) and the Linear
Regression Channel breakout-with-volume-confirm strategy
(linreg_channel_breakout_volconfirm) already in this repo -- this is the
first strategy using R-squared itself (not just the slope/channel) as a
standalone trend-quality GATE.

Signal logic
------------
- Rolling OLS of close on a 0..N-1 time index over `reg_window` bars;
  compute R-squared and the fitted slope for each window.
- Entry (long): R-squared >= r2_threshold AND slope > 0 (clean, positive
  trend).
- Exit: R-squared drops below r2_threshold (trend quality degraded) OR
  slope turns <= 0 (trend direction flips), OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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


def _rolling_r2_slope(close: pd.Series, window: int) -> tuple[pd.Series, pd.Series]:
    """Rolling OLS R-squared and slope of close vs. a 0..window-1 time index."""
    n = len(close)
    r2 = np.full(n, np.nan)
    slope = np.full(n, np.nan)
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    x_centered = x - x_mean
    ss_xx = (x_centered ** 2).sum()

    vals = close.to_numpy(dtype=float)
    for i in range(window - 1, n):
        y = vals[i - window + 1 : i + 1]
        if np.isnan(y).any():
            continue
        y_mean = y.mean()
        y_centered = y - y_mean
        ss_xy = (x_centered * y_centered).sum()
        b = ss_xy / ss_xx if ss_xx > 0 else 0.0
        y_pred = b * x_centered + y_mean
        ss_res = ((y - y_pred) ** 2).sum()
        ss_tot = (y_centered ** 2).sum()
        r2_val = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        r2[i] = r2_val
        slope[i] = b

    return pd.Series(r2, index=close.index), pd.Series(slope, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    reg_window: int = 20,
    r2_threshold: float = 0.8,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    r2, slope = _rolling_r2_slope(close, reg_window)

    entry = (r2 >= r2_threshold) & (slope > 0)
    exit_cond = (r2 < r2_threshold) | (slope <= 0)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cond.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
