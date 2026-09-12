"""Strategy: Kaufman "Inside Channel" linear-regression band mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-12-188):
Per Perry Kaufman's TASC 5/2025 article, covered at
https://financial-hacker.com/trading-the-channel/ ("Trading the Channel"):
fit a rolling linear-regression line over the last N closes, then build an
upper/lower channel from the max/min deviation of price from that line over
the same window. Kaufman's "Inside Channel" method (per the source, "the
most profitable" of the several he tested) opens a long when price comes
within a `Zone` distance of the lower band, and flattens/exits when price
comes within `Zone` of the upper band. Economic rationale (source's own):
a regression-fit channel captures the *local* trend's typical excursion
range, so a touch of the near band without exceeding it further indicates
a stall/pullback-to-mean-of-trend-channel rather than a breakout -- distinct
from a static-lookback Bollinger/Donchian band because the reference line
itself is a fitted trend, not a simple SMA.

This is architecturally distinct from the previously-tested LRC pullback
continuation strategy (2026-09-12-150, id in
2026-09-12_lrc_pullback_continuation.py) which required slope>0 AND a
prior undershoot-then-reclaim of the *center* regression line as a trend
*continuation* signal. Here there is no slope/trend-direction filter at
all -- entries/exits are purely proximity-to-band (source's literal
mean-reversion "Inside Channel" rule), trading the bands themselves rather
than the center line, long-only (source's WFO variant flips long/short;
we keep long-only per repo convention of avoiding unnecessary shorting
complexity while still testing the core edge).

Signal logic
------------
For each bar t, using the trailing `lrc_window` (N) closes ending at t:
  - Fit OLS regression: close ~ a + b * bar_index (bar_index 0..N-1,
    oldest to newest).
  - LinVal[t] = the regression's fitted value at the *last* bar in the
    window (i.e. today's fitted trend value).
  - For each of the N bars in the window, compute the deviation of that
    day's actual close from the regression line's fitted value on that
    day; HighDev[t] = max deviation (>=0 clipped), LowDev[t] = min
    deviation (<=0 clipped).
  - Zone[t] = zone_factor * (HighDev[t] + LowDev[t])  -- literal formula
    from the source article (Petra Volkova's own code), including the
    quirk (noted by a commenter and acknowledged by the author) that this
    is not a symmetric inner zone but the best-performing variant the
    source found empirically; we keep it as specified rather than
    "fixing" it, since the source explicitly reports the "fixed" version
    (Factor*(HighDev-LowDev)) performed worse.
  - Long entry: close <= LinVal + LowDev + Zone (price near/through lower
    band).
  - Exit (flatten): close >= LinVal + HighDev - Zone (price near/through
    upper band).
  - Otherwise carry forward previous position (no change) -- this mirrors
    Kaufman's original "hold until opposite band is touched" rather than a
    fixed max-hold, since the source's own system has no time-stop.

Interface contract for validators (see validation/validators.py) and
grid_test (see validation/grid_test.py):
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        {0, 1} position series aligned to price_df.index.
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
        Daily strategy returns (position-weighted, no transaction costs
        applied here).

Tunable params (all keyword args, per RESEARCH_LOOP.md Step 5 contract):
    lrc_window   (N, default 40)   -- regression/channel lookback in bars.
    zone_factor  (Factor, default 0.2) -- inner-zone fraction of band width.
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


def _rolling_channel(close: pd.Series, lrc_window: int):
    """Vectorized-ish rolling OLS regression channel.

    Returns (lin_val, high_dev, low_dev) aligned to `close`'s index, NaN for
    bars before the first full window.
    """
    n = lrc_window
    x = np.arange(n, dtype=float)
    x_mean = x.mean()
    x_centered = x - x_mean
    denom = (x_centered ** 2).sum()

    vals = close.to_numpy(dtype=float)
    m = len(vals)
    lin_val = np.full(m, np.nan)
    high_dev = np.full(m, np.nan)
    low_dev = np.full(m, np.nan)

    for t in range(n - 1, m):
        window = vals[t - n + 1 : t + 1]
        y_mean = window.mean()
        slope = ((x_centered) * (window - y_mean)).sum() / denom
        intercept = y_mean - slope * x_mean
        fitted = intercept + slope * x  # fitted values for the whole window
        dev = window - fitted
        lin_val[t] = fitted[-1]  # today's fitted trend value
        high_dev[t] = max(dev.max(), 0.0)
        low_dev[t] = min(dev.min(), 0.0)

    return (
        pd.Series(lin_val, index=close.index),
        pd.Series(high_dev, index=close.index),
        pd.Series(low_dev, index=close.index),
    )


def generate_signals(
    price_df: pd.DataFrame,
    lrc_window: int = 40,
    zone_factor: float = 0.2,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    lin_val, high_dev, low_dev = _rolling_channel(close, lrc_window)
    zone = zone_factor * (high_dev + low_dev)

    lower_trigger = lin_val + low_dev + zone
    upper_trigger = lin_val + high_dev - zone

    position = pd.Series(0, index=close.index, dtype=int)
    pos = 0
    for i in range(len(close)):
        if np.isnan(lin_val.iloc[i]):
            position.iloc[i] = 0
            continue
        c = close.iloc[i]
        if c <= lower_trigger.iloc[i]:
            pos = 1
        elif c >= upper_trigger.iloc[i]:
            pos = 0
        position.iloc[i] = pos

    return position.fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    lrc_window: int = 40,
    zone_factor: float = 0.2,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = generate_signals(price_df, lrc_window=lrc_window, zone_factor=zone_factor)
    # Trade on next bar's return using yesterday's signal (avoid lookahead).
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
