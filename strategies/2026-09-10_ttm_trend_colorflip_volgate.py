"""Strategy: TTM Trend bar-color trend-following, with an added
realized-volatility regime gate (direct follow-up to near-miss
2026-09-10-080).

Hypothesis (see knowledge_base/strategies_log.jsonl id, this iteration):
Direct follow-up to near-miss 2026-09-10-080 (plain TTM Trend color-flip +
SMA trend filter, accepted SPY only, QQQ full-sample Sharpe 0.916 --a
narrow miss vs the 1.0 threshold). That entry's own Step 6 grid summary
showed the edge concentrated heavily in the low-vol tercile (12/24 passing
cells) vs mid (2/24) and high (1/24) -- the same regime-dependence pattern
that this repo has repeatedly found rescues near-miss trend-following
strategies elsewhere (e.g. 2026-09-03_bb_meanrev_qqq_volregime.py,
2026-09-08-043 VQI+vol-gate). This variant adds an explicit realized-vol
regime gate (20d realized vol <= its trailing 252d median, identical
construction to the repo's established vol-gate pattern) restricting
entries to the low-vol regime only, keeping the underlying TTM Trend
color-flip + SMA trend-filter entry/exit logic completely unchanged
otherwise, to isolate whether the gate alone pushes QQQ's full-sample
Sharpe over the 1.0 threshold.

Signal logic
------------
- midpoint[t] = (high[t] + low[t]) / 2
- reference[t] = mean(midpoint[t-lookback : t])
- up_bar/down_bar color exactly as in 2026-09-10_ttm_trend_colorflip.py
- Low-vol regime: 20-day realized vol (annualized std of daily log
  returns) <= its trailing 252-day median * vol_regime_ratio (default 1.0).
- Entry (long): color flips from down to up AND close > SMA(trend_window)
  AND we are in the low-vol regime.
- Exit: color flips back to down, OR the trend filter breaks, OR the
  volatility regime flips to high-vol (new exit condition vs the parent
  strategy), OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _ttm_trend_color(df: pd.DataFrame, lookback: int) -> pd.Series:
    """Return +1 (up bar), -1 (down bar) per bar, carrying forward on ties."""
    midpoint = (df["high"] + df["low"]) / 2.0
    reference = midpoint.rolling(lookback).mean().shift(1)
    close = df["close"]

    raw = pd.Series(np.nan, index=close.index)
    raw[close > reference] = 1
    raw[close < reference] = -1
    color = raw.ffill()
    return color


def _low_vol_regime(close: pd.Series, vol_window: int, vol_lookback: int, vol_regime_ratio: float) -> pd.Series:
    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median_1y = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    return (realized_vol <= (vol_median_1y * vol_regime_ratio)).fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    lookback: int = 6,
    trend_window: int = 100,
    max_hold_days: int = 30,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    color = _ttm_trend_color(df, lookback)
    prev_color = color.shift(1)
    up_flip = (prev_color == -1) & (color == 1)
    down_flip = (prev_color == 1) & (color == -1)

    sma = close.rolling(trend_window).mean()
    trend_up = close > sma

    low_vol_regime = _low_vol_regime(close, vol_window, vol_lookback, vol_regime_ratio)

    entry = up_flip.fillna(False) & trend_up.fillna(False) & low_vol_regime
    exit_condition = down_flip.fillna(False) | (~trend_up.fillna(False)) | (~low_vol_regime)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_condition.iloc[i]) or held >= max_hold_days:
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
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
