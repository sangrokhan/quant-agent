"""Strategy: Ehlers Super Smoother trend filter with inverse-realized-vol
sizing overlay, direct fix for 2026-09-17-088's QQQ near-miss.

Hypothesis (direct fix, no new external research needed -- Super Smoother
formula/rules already confirmed at 2026-09-17-088 this cron trigger):
2026-09-17-088 tested the binary long/flat Super Smoother slope+
price-above-line trend filter: accepted on SPY (period=30) but QQQ
(period=30) was a near-miss -- only Sharpe (0.887) failed, MDD/TC-survival/
walk-forward/parameter-sensitivity all passed. This iteration applies this
repo's standard rescue pattern (already validated for HalfTrend earlier
this same cron trigger, 2026-09-17-084): scale exposure inversely to
rolling realized volatility (target_vol / realized_vol, clipped to
leverage_cap) on top of the same binary Super Smoother gate.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap])
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _super_smoother(price: pd.Series, period: int) -> pd.Series:
    a1 = math.exp(-1.414 * math.pi / period)
    b1 = 2 * a1 * math.cos(math.radians(1.414 * 180.0 / period))
    c2 = b1
    c3 = -(a1 ** 2)
    c1 = 1 - c2 - c3

    price_arr = price.to_numpy()
    n = len(price_arr)
    ss = np.zeros(n)

    for i in range(n):
        if i == 0:
            ss[i] = price_arr[i]
        elif i == 1:
            ss[i] = (price_arr[i] + price_arr[i - 1]) / 2.0
        else:
            ss[i] = (
                c1 * (price_arr[i] + price_arr[i - 1]) / 2.0
                + c2 * ss[i - 1]
                + c3 * ss[i - 2]
            )

    return pd.Series(ss, index=price.index)


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 30,
    vol_window: int = 20,
    target_vol: float = 0.15,
    leverage_cap: float = 1.5,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series.

    Binary Super Smoother slope+price-above-line gate scaled by an
    inverse-realized-volatility exposure multiplier.
    """
    df = _prep(price_df)
    close = df["close"]

    ss = _super_smoother(close, period)
    slope_positive = ss.diff() > 0
    above_line = close > ss
    gate = (slope_positive & above_line).fillna(False).astype(float)

    daily_ret = close.pct_change()
    realized_vol = daily_ret.rolling(vol_window, min_periods=vol_window // 2).std() * np.sqrt(252)
    vol_scalar = (target_vol / realized_vol.replace(0.0, np.nan)).clip(upper=leverage_cap)
    vol_scalar = vol_scalar.fillna(0.0)

    exposure = (gate * vol_scalar).clip(lower=0.0, upper=leverage_cap)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    period: int = 30,
    vol_window: int = 20,
    target_vol: float = 0.15,
    leverage_cap: float = 1.5,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        period=period,
        vol_window=vol_window,
        target_vol=target_vol,
        leverage_cap=leverage_cap,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
