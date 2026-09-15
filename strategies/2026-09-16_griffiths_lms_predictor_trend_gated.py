"""Strategy: Ehlers Griffiths (LMS Adaptive) Predictor (TASC Jan 2025,
"Linear Predictive Filters And Instantaneous Frequency") trend-following
long entry on a forward-forecast upturn, gated by an SMA trend filter.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per traders.com's exact disclosed EasyLanguage source (TASC January 2025
Traders' Tips, John F. Ehlers, "Linear Predictive Filters And Instantaneous
Frequency", from Griffiths' 1975 IEEE ASSP-23 paper "Rapid Measurement of
Digital Instantaneous Frequency",
https://traders.com/Documentation/FEEDbk_docs/2025/01/TradersTips.html,
found via a systematic browser_exec scan of the TASC Traders' Tips archive
after web_search returned no useful results this iteration):

1. HP = 2-pole HighPass(close, upper_bound) strips slow drift.
2. Signal = SuperSmoother(HP, lower_bound), peak-normalized by a decaying
   running peak (Peak *= 0.991 each bar unless a new |Signal| high is set)
   so Signal oscillates roughly within [-1, +1] -- a bandpass-filtered,
   self-normalizing cycle-swing signal (similar spirit to EBSW/Cybernetic
   Oscillator already tested, but normalized by a decaying peak rather than
   RMS).
3. An LMS (least-mean-squares) adaptive linear predictor with `lms_length`
   taps is trained online each bar: it predicts the current Signal value
   from the `lms_length` most recent PAST Signal values, computes the
   prediction error, and nudges its coefficient vector by
   `mu * error * lagged_value` (mu = 1/lms_length) -- a textbook adaptive
   AR predictor, distinct from every fixed-coefficient Ehlers filter
   already tested in this repo (Cyber Cycle, Roofing Filter, Reversion
   Index, Continuation Index, Laguerre family) because its weights adapt
   online to the data's own recent autocorrelation structure rather than
   using a fixed cutoff-period formula.
4. The trained predictor is then used to forecast `bars_fwd` steps ahead
   (`XPred`), Ehlers' own disclosed forward-projection step.

Trading rule (not explicitly given by Ehlers for this indicator -- he
presents it as a signal-processing tool, not a packaged strategy; this is
the Research Agent's own economically-motivated rule per RESEARCH_LOOP.md
Step 4): long when the forward forecast XPred exceeds the current Signal by
more than `entry_threshold` (the adaptive predictor forecasts an upturn in
the underlying cycle), gated by an SMA(trend_window) uptrend filter (since
Griffiths' bandpass Signal alone is cycle/mean-reversion-oriented and needs
a directional filter to avoid buying into a strong downtrend's local
cyclical bounces), with a max_hold_days time-stop backstop.

First Griffiths/LMS-adaptive-predictive-filter strategy in this repo.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position series)
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


def _highpass(src: pd.Series, period: int) -> pd.Series:
    """Ehlers' 2-pole highpass filter."""
    a1 = math.exp(-1.414 * math.pi / period)
    b1 = 2.0 * a1 * math.cos(1.414 * math.pi / period)
    c2 = b1
    c3 = -a1 * a1
    c1 = (1.0 + c2 - c3) / 4.0

    vals = src.ffill().fillna(0.0).to_numpy()
    n = len(vals)
    hp = np.zeros(n)
    for i in range(n):
        if i < 2:
            hp[i] = 0.0
        else:
            hp[i] = c1 * (vals[i] - 2.0 * vals[i - 1] + vals[i - 2]) + c2 * hp[i - 1] + c3 * hp[i - 2]
    return pd.Series(hp, index=src.index)


def _super_smoother(series: pd.Series, period: int) -> pd.Series:
    """Ehlers' 2-pole SuperSmoother filter."""
    a1 = math.exp(-1.414 * math.pi / period)
    b1 = 2.0 * a1 * math.cos(1.414 * math.pi / period)
    c2 = b1
    c3 = -a1 * a1
    c1 = 1.0 - c2 - c3

    vals = series.fillna(0.0).to_numpy()
    n = len(vals)
    ss = np.zeros(n)
    for i in range(n):
        if i < 2:
            ss[i] = vals[i]
        else:
            ss[i] = c1 * (vals[i] + vals[i - 1]) / 2.0 + c2 * ss[i - 1] + c3 * ss[i - 2]
    return pd.Series(ss, index=series.index)


def _griffiths_signal_and_forecast(
    close: pd.Series,
    upper_bound: int,
    lower_bound: int,
    lms_length: int,
    bars_fwd: int,
) -> tuple[pd.Series, pd.Series]:
    """Returns (Signal, XPred): the peak-normalized bandpass Signal and its
    LMS-adaptive-predictor bars_fwd-ahead forecast.
    """
    hp = _highpass(close, upper_bound)
    lp = _super_smoother(hp, lower_bound)

    lp_vals = lp.to_numpy()
    n = len(lp_vals)
    signal = np.zeros(n)
    peak = 0.1
    for i in range(n):
        peak *= 0.991
        if abs(lp_vals[i]) > peak:
            peak = abs(lp_vals[i])
        signal[i] = lp_vals[i] / peak if peak != 0 else 0.0

    mu = 1.0 / lms_length
    coef = np.zeros(lms_length)
    xpred = np.zeros(n)
    for t in range(n):
        if t < lms_length:
            xpred[t] = signal[t]
            continue
        # lagged window: v[0] = signal[t-1] (most recent past), ..., v[L-1] = signal[t-L]
        v = signal[t - lms_length : t][::-1]
        pred_current = float(np.dot(coef, v))
        error = signal[t] - pred_current
        coef = coef + mu * error * v

        # Forward forecast: iteratively predict bars_fwd steps ahead using
        # the just-updated coefficients and a rolling forecast window.
        window = list(signal[t - lms_length + 1 : t + 1][::-1])  # most-recent-first
        forecast = None
        for _ in range(bars_fwd):
            forecast = float(np.dot(coef, window[:lms_length]))
            window = [forecast] + window[: lms_length - 1]
        xpred[t] = forecast if forecast is not None else signal[t]

    return pd.Series(signal, index=close.index), pd.Series(xpred, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    upper_bound: int = 40,
    lower_bound: int = 18,
    lms_length: int = 18,
    bars_fwd: int = 2,
    entry_threshold: float = 0.3,
    max_hold_days: int = 15,
) -> pd.Series:
    """0/1 long-only position series.

    Entry: LMS-adaptive forward forecast (XPred) exceeds current Signal by
    more than entry_threshold (predicted cyclical upturn), gated by
    close > SMA(trend_window).
    Exit: forecast/signal gap closes back below entry_threshold/2, the
    trend filter breaks, or max_hold_days bars elapse, whichever first.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    signal, xpred = _griffiths_signal_and_forecast(
        close, upper_bound, lower_bound, lms_length, bars_fwd
    )
    gap = xpred - signal

    entry_trigger = ((gap > entry_threshold) & trend_long.fillna(False)).to_numpy()
    exit_trigger = ((gap < entry_threshold / 2.0) | (~trend_long.fillna(False))).to_numpy()

    n = len(close)
    position = np.zeros(n)
    in_pos = False
    bars_held = 0
    for i in range(n):
        if in_pos:
            bars_held += 1
            if exit_trigger[i] or bars_held >= max_hold_days:
                in_pos = False
                bars_held = 0
            else:
                position[i] = 1.0
        else:
            if entry_trigger[i]:
                in_pos = True
                bars_held = 0
                position[i] = 1.0

    return pd.Series(position, index=close.index)


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    upper_bound: int = 40,
    lower_bound: int = 18,
    lms_length: int = 18,
    bars_fwd: int = 2,
    entry_threshold: float = 0.3,
    max_hold_days: int = 15,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        trend_window=trend_window,
        upper_bound=upper_bound,
        lower_bound=lower_bound,
        lms_length=lms_length,
        bars_fwd=bars_fwd,
        entry_threshold=entry_threshold,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret
