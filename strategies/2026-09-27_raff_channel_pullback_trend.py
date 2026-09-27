"""Strategy: Raff Channel (equidistant regression channel) pullback-in-trend.

Hypothesis (2026-09-27 KB entry, this iteration):
The Raff Channel (Gilbert Raff) fits a rolling linear-regression midline over
``reg_window`` bars, then draws two PARALLEL lines offset by the MAXIMUM
absolute historical deviation of price from that line over the same window
(an equidistant channel, NOT a standard-deviation/standard-error band like
Bollinger/Kirshenbaum/PJK/STARC already in this repo). Source:
https://quantifiedtrader.com/backtest/strategies/raff-channel (site's own
naive rule: price above midline = long, i.e. a bare regression-slope trend
filter). This iteration adapts it into a PULLBACK-IN-TREND entry instead of
the site's naive always-in trend rule (per this repo's established pattern
of turning naive site rules into slope-gated pullback entries, e.g.
2026-09-18-119 PJK Channels Rule 3): only buy when the regression slope is
positive (confirmed uptrend) AND price pulls back down to touch/dip below
the LOWER equidistant band (a stretched throwback, not a breakout) --
betting the reversion is back toward the midline, not a channel breakout.
Exit on close crossing back above the midline (mean-reversion target), the
slope turning non-positive (trend break), or a max_hold_days time-stop.

First Raff-Channel / equidistant-regression-channel strategy in this repo
(0 prior knowledge_base hits for "Raff") -- distinct from all other
regression-channel families already tested (Linear Regression Channel
[[[std-dev residual bands, 2026-09-04-141]]], Standard Error Bands
[[[linreg-stderr bands, 2026-09-06-126]]], PJK Channels [[[same construction
as Std Err Bands, 2026-09-18-116/119]]], Standard Deviation Channel
[[[pullback-to-line, not band-touch, 2026-09-08-100]]]) because the band
half-width here is the empirical max-abs-deviation over the window, not a
statistical dispersion measure.

Interface contract for validators/grid_test (see RESEARCH_LOOP.md Step 5):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def _raff_channel(close: pd.Series, reg_window: int):
    """Rolling linear-regression midline + equidistant upper/lower bands.

    For each window ending at bar i: fit close[i-reg_window+1 : i+1] against
    time index [0..reg_window-1], evaluate the fitted line's value AT THE
    LAST POINT (the midline value "as of today", non-repainting -- no
    future bars used), and set the band half-width to the max absolute
    residual (|close - fitted_line|) observed anywhere within that same
    window (the classic Raff/equidistant-channel construction).
    """
    n = len(close)
    mid = np.full(n, np.nan)
    half_width = np.full(n, np.nan)
    slope = np.full(n, np.nan)
    x = np.arange(reg_window, dtype=float)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()

    vals = close.values
    for i in range(reg_window - 1, n):
        window = vals[i - reg_window + 1 : i + 1]
        y_mean = window.mean()
        b = ((x - x_mean) * (window - y_mean)).sum() / x_var
        a = y_mean - b * x_mean
        fitted = a + b * x
        resid = window - fitted
        mid[i] = fitted[-1]
        half_width[i] = np.max(np.abs(resid))
        slope[i] = b

    mid_s = pd.Series(mid, index=close.index)
    hw_s = pd.Series(half_width, index=close.index)
    slope_s = pd.Series(slope, index=close.index)
    upper = mid_s + hw_s
    lower = mid_s - hw_s
    return mid_s, upper, lower, slope_s


def generate_signals(
    price_df: pd.DataFrame,
    reg_window: int = 30,
    slope_min_pct: float = 0.0,
    max_hold_days: int = 15,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    slope_min_pct: minimum regression slope, expressed as a fraction of the
    midline value per bar (slope / mid), required to consider the trend
    "up" (0.0 = any positive slope qualifies; can be raised to require a
    steeper trend).

    vol_regime_ratio: grid-diagnosed edge is concentrated in the low
    realized-vol tercile (mid/high tercile Sharpe negative/near-zero across
    both QQQ and SPY) -- per this repo's established rescue pattern (e.g.
    2026-09-03_bb_meanrev_qqq_volregime.py), only trade while trailing
    vol_window-day realized vol is <= vol_regime_ratio x its trailing
    vol_lookback-day median (a "low-vol regime" gate); flatten immediately
    on a regime flip to high-vol, same as the exit logic below.
    """
    import math

    df = _prep(price_df)
    close = df["close"]

    daily_log_ret = (close / close.shift(1)).apply(
        lambda r: math.log(r) if r and r > 0 else None
    ).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    low_vol_regime = (realized_vol <= (vol_median * vol_regime_ratio)).fillna(False)

    mid, upper, lower, slope = _raff_channel(close, reg_window)
    slope_pct = slope / mid.replace(0, np.nan)

    uptrend = slope_pct > slope_min_pct
    touch_lower = close <= lower
    entry = (touch_lower & uptrend & low_vol_regime).fillna(False)

    exit_meanrev = (close >= mid).fillna(False)
    exit_trend_break = (~uptrend).fillna(False)
    exit_regime_flip = (~low_vol_regime).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or bool(exit_trend_break.iloc[i]) or bool(exit_regime_flip.iloc[i]) or held >= max_hold_days:
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
