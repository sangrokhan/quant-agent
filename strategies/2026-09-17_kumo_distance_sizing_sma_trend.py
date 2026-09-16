"""Strategy: SMA(trend_window) directional gate with continuous Ichimoku
Kumo-distance sizing overlay + deadband, leverage-cap-aware for crypto from
the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
This repo has 6 prior Ichimoku entries: TK-cross+cloud-confirmation binary
trigger (2026-09-04-034, near-miss rejected), Kumo breakout binary trigger
(2026-09-05-049), 3-condition TK+cloud+Chikou confluence (2026-09-05-085),
and a standalone Chikou-Span-distance continuous sizing dial
(2026-09-14-163, accepted QQQ only). None of these use the price-to-Kumo
DISTANCE itself (as opposed to a binary above/below-cloud state) as a
continuous signal. Per common Ichimoku trading literature (e.g.
agentictraders.io, j2t.com -- "the wider the cloud/greater the distance
from price to Kumo, the stronger the confirmed trend"), the vertical gap
between price and the nearer Kumo boundary is itself informative about
trend conviction, not just its sign. This iteration reframes that price-
to-Kumo distance as a CONTINUOUS SIZING dial (rolling z-score + tanh)
within an SMA(trend_window) uptrend gate, following this repo's now-
established binary-oscillator-to-continuous-sizing-dial rescue pattern
(successful for Chikou Span itself, DPO, Hurst, VHF, TII, RVI, MAMA-FAMA
spread, Kalman slope, SKEW Index). First Kumo-DISTANCE (as opposed to
Chikou-distance or cloud-breakout) continuous-sizing variant in this repo.

Ichimoku Kumo construction (standard periods, e.g. per
quantifiedstrategies.com's Ichimoku Cloud article already cited in
2026-09-04-034):
    Tenkan-sen = (9-period high + 9-period low) / 2
    Kijun-sen = (26-period high + 26-period low) / 2
    Senkou Span A = (Tenkan + Kijun) / 2, plotted 26 periods forward
    Senkou Span B = (52-period high + 52-period low) / 2, plotted 26
        periods forward
    Kumo = area between Senkou Span A and B

For a same-bar-usable signal (no forward-looking data), this construction
uses the UN-SHIFTED Senkou Span A/B values (i.e. what the cloud will look
like 26 bars from now, computed from data available today) as the
reference cloud boundaries for TODAY's distance calculation -- this
deliberately mirrors how Ichimoku is read in practice (the current cloud
boundary visible on today's bar is the span A/B value computed
`displacement` bars ago), avoiding any lookahead.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
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


def _kumo_boundaries(
    high: pd.Series,
    low: pd.Series,
    tenkan_period: int = 9,
    kijun_period: int = 26,
    senkou_b_period: int = 52,
    displacement: int = 26,
):
    """Return (span_a, span_b) as they'd appear on TODAY's bar (i.e.
    already shifted forward by `displacement`, so no lookahead: span_a[t]
    and span_b[t] are computed from data available at t-displacement)."""
    tenkan = (high.rolling(tenkan_period).max() + low.rolling(tenkan_period).min()) / 2.0
    kijun = (high.rolling(kijun_period).max() + low.rolling(kijun_period).min()) / 2.0
    span_a_raw = (tenkan + kijun) / 2.0
    span_b_raw = (high.rolling(senkou_b_period).max() + low.rolling(senkou_b_period).min()) / 2.0

    span_a = span_a_raw.shift(displacement)
    span_b = span_b_raw.shift(displacement)
    return span_a, span_b


def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
    raw = raw_exposure.fillna(0.0).to_numpy()
    held = np.zeros_like(raw)
    current = 0.0
    for i, r in enumerate(raw):
        if abs(r - current) > deadband:
            current = r
        held[i] = current
    return pd.Series(held, index=raw_exposure.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    tenkan_period: int = 9,
    kijun_period: int = 26,
    senkou_b_period: int = 52,
    displacement: int = 26,
    zscore_window: int = 60,
    sensitivity: float = 0.6,
    base_exposure: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    dial = tanh(zscore(distance, zscore_window)), where distance = close
    minus the nearer Kumo boundary (max(span_a, span_b) when close is
    above the cloud, i.e. the top of the cloud -- a positive distance
    means how far above the cloud price is; the dial only matters when the
    SMA trend gate is already long, so distance is computed relative to
    the cloud TOP consistently). Gated to 0 whenever close is below its
    SMA(trend_window).
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    trend_long = close > close.rolling(trend_window).mean()

    span_a, span_b = _kumo_boundaries(
        high, low, tenkan_period=tenkan_period, kijun_period=kijun_period,
        senkou_b_period=senkou_b_period, displacement=displacement,
    )
    cloud_top = pd.concat([span_a, span_b], axis=1).max(axis=1)
    distance = close - cloud_top

    roll_mean = distance.rolling(zscore_window).mean()
    roll_std = distance.rolling(zscore_window).std(ddof=0)
    z = (distance - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(z.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    tenkan_period: int = 9,
    kijun_period: int = 26,
    senkou_b_period: int = 52,
    displacement: int = 26,
    zscore_window: int = 60,
    sensitivity: float = 0.6,
    base_exposure: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        tenkan_period=tenkan_period,
        kijun_period=kijun_period,
        senkou_b_period=senkou_b_period,
        displacement=displacement,
        zscore_window=zscore_window,
        sensitivity=sensitivity,
        base_exposure=base_exposure,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
