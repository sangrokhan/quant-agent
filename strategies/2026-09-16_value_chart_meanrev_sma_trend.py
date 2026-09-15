"""Strategy: David Stendahl's Value Chart (VC) mean-reversion oscillator,
gated by an SMA(trend_window) directional filter, continuous sizing dial.

Hypothesis (knowledge_base id TBD, this cron trigger):
The Value Chart (David Stendahl, "Dynamic Trading") de-trends OHLC prices
against a basis moving average of the bar midpoint, then rescales the
result by a volatility unit (average high-low range / 5) so the output
oscillates on an approximately +-10 integer grid regardless of the
instrument's absolute price level or volatility regime. Per source
(Google AI-overview synthesis of Scribd "Dynamic Trading Indicators
Overview"/"Advanced Technical Indicators in Excel" PDFs, corroborating a
prior dead-end attempt to source this from kaabar-sofien.medium.com which
404'd this same cron trigger):

    Midpoint = (High + Low) / 2
    BasisMA  = SMA(Midpoint, N)
    LRange   = SMA(High - Low, N) / 5
    VClose   = (Close - BasisMA) / LRange

VClose > +6..+8 is "overbought" (stretched above fair value), < -6..-8 is
"oversold" (stretched below fair value); -6..+6 is the neutral/fair-value
zone. This repo has exactly 1 prior "Value Chart" index entry (a dead-end
research log, not an implementation) -- this is the first actual
implementation. Reframed here as a continuous mean-reversion sizing dial:
exposure is proportional to -tanh(VClose / scale) (short bias when
overbought, long bias when oversold), gated to only fire in the direction
of the broader SMA(trend_window) trend (buy-the-dip in an uptrend / avoid
fighting a downtrend), with a deadband around the neutral zone to reduce
churn. Economic rationale: on trending, liquid instruments, short-term
overbought/oversold stretches relative to a fair-value band tend to mean-
revert within the dominant trend rather than reverse it outright.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [-leverage_cap, +leverage_cap], though gated to [0, leverage_cap]
    when long_only=True for equities without cheap shorting).
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


def _compute_value_chart(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    vc_window: int = 5,
) -> pd.Series:
    """Stendahl Value Chart close component (VClose), standard formula:
    Midpoint = (H+L)/2; BasisMA = SMA(Midpoint, N); LRange = SMA(H-L, N)/5;
    VClose = (Close - BasisMA) / LRange. Divide-by-zero guarded with a tiny
    epsilon (LRange collapses to 0 only on fully flat synthetic data)."""
    midpoint = (high + low) / 2.0
    basis_ma = midpoint.rolling(vc_window, min_periods=vc_window).mean()
    lrange = (high - low).rolling(vc_window, min_periods=vc_window).mean() / 5.0
    lrange = lrange.replace(0.0, np.nan)
    vclose = (close - basis_ma) / lrange
    return vclose


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    vc_window: int = 5,
    scale: float = 8.0,
    deadband: float = 0.15,
    leverage_cap: float = 1.0,
    long_only: bool = True,
    smooth_span: int = 1,
) -> pd.Series:
    """Continuous exposure in [0, leverage_cap] (long_only) or
    [-leverage_cap, leverage_cap] (long_only=False): mean-revert against
    Value Chart stretch, gated by SMA(trend_window) trend direction, with a
    deadband around the neutral VClose zone to reduce churn.
    ``smooth_span`` (>1) applies an EMA to the dial before the deadband
    step, to reduce whipsaw/turnover at the cost of signal timeliness."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    vc = _compute_value_chart(high, low, close, vc_window=vc_window)
    # Mean-reversion dial: negative VClose (oversold) -> positive dial value.
    dial = -np.tanh(vc / scale)
    if smooth_span and smooth_span > 1:
        dial = dial.ewm(span=smooth_span, min_periods=1).mean()

    trend_sma = close.rolling(trend_window, min_periods=trend_window).mean()
    uptrend = close > trend_sma

    exposure = dial.copy()
    exposure[exposure.abs() < deadband] = 0.0

    if long_only:
        exposure = exposure.clip(lower=0.0)
        exposure = exposure.where(uptrend, 0.0)
    else:
        # Only take reversion trades in the direction consistent with the
        # broader trend (long dips in an uptrend, short rallies in a
        # downtrend); zero out counter-trend trades entirely.
        long_leg = exposure.clip(lower=0.0).where(uptrend, 0.0)
        short_leg = exposure.clip(upper=0.0).where(~uptrend, 0.0)
        exposure = long_leg + short_leg

    exposure = exposure.clip(lower=-leverage_cap, upper=leverage_cap)
    exposure = exposure.fillna(0.0)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    vc_window: int = 5,
    scale: float = 8.0,
    deadband: float = 0.15,
    leverage_cap: float = 1.0,
    long_only: bool = True,
    smooth_span: int = 1,
) -> pd.Series:
    """Daily strategy returns: prior-bar exposure (avoid lookahead) times
    that bar's close-to-close return."""
    df = _prep(price_df)
    exposure = generate_signals(
        df,
        trend_window=trend_window,
        vc_window=vc_window,
        scale=scale,
        deadband=deadband,
        leverage_cap=leverage_cap,
        long_only=long_only,
        smooth_span=smooth_span,
    )
    asset_returns = df["close"].pct_change()
    strat_returns = exposure.shift(1).fillna(0.0) * asset_returns
    return strat_returns.fillna(0.0)
