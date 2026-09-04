"""Strategy: Ehlers Roofing Filter (HP+SuperSmoother) SMA-signal-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-012):
John Ehlers' Roofing Filter is a two-stage digital filter: a 2-pole
highpass filter (removes cycles longer than highpass_period bars, i.e.
strips long-term trend/drift) followed by a SuperSmoother lowpass filter
(removes high-frequency noise shorter than lowpass_period bars). The
result "hugs price closely with far less jitter than a typical moving
average" and turns 2-3 bars earlier than a comparable EMA (per
theindicatorlab.com's review). Concrete mechanical rule (same source):
long entry when the Roofing Filter line crosses above its own 3-period
SMA signal line, gated by close above a 200-period EMA trend filter;
exit when price closes below the filter line, or the reverse crossover.

Exact HP+SuperSmoother coefficient formula per ProRealCode's
EasyLanguage-derived transcription of Ehlers' own published code
(https://www.prorealcode.com/prorealtime-indicators/my-stochastic-oscillator-john-ehlers/,
which documents the identical HP+SuperSmoother "Filt" construction that
also underlies MESA Stochastic).

First strategy in this repo using the Roofing Filter line directly as a
trend-following crossover signal (SMA(3)-signal-line crossover) --
distinct from MESA Stochastic (id=2026-09-04-118, already tested/
rejected in this repo), which converts the SAME underlying HP+
SuperSmoother "Filt" construction into a bounded 0-1 stochastic
oscillator traded with overbought/oversold countertrend thresholds
rather than this trend-following crossover-with-trend-filter approach.

Formula (2-pole highpass + SuperSmoother, per Ehlers/ProRealCode):
  alpha1 = (cos(0.707*2*pi/highpass_period) + sin(0.707*2*pi/highpass_period) - 1)
           / cos(0.707*2*pi/highpass_period)
  HP_t = (1-alpha1/2)^2 * (close_t - 2*close_{t-1} + close_{t-2})
         + 2*(1-alpha1)*HP_{t-1} - (1-alpha1)^2*HP_{t-2}

  a1 = exp(-1.414*pi/lowpass_period)
  b1 = 2*a1*cos(1.414*pi/lowpass_period)
  c2 = b1; c3 = -a1^2; c1 = 1 - c2 - c3
  Filt_t = c1*(HP_t + HP_{t-1})/2 + c2*Filt_{t-1} + c3*Filt_{t-2}

Signal logic
------------
- Entry (long): Filt crosses above SMA(Filt, signal_window) AND close is
  above EMA(trend_window) (uptrend gate).
- Exit: Filt crosses below SMA(Filt, signal_window), OR close closes
  below the Filt line itself (source's alternate trailing-exit rule),
  OR a max_hold_days time-stop backstop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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


def _roofing_filter(close: pd.Series, highpass_period: int, lowpass_period: int) -> pd.Series:
    c = close.to_numpy()
    n = len(c)

    rad = 0.707 * 2.0 * math.pi / highpass_period
    alpha1 = (math.cos(rad) + math.sin(rad) - 1.0) / math.cos(rad)

    hp = np.zeros(n)
    for i in range(2, n):
        hp[i] = (
            (1 - alpha1 / 2.0) ** 2 * (c[i] - 2 * c[i - 1] + c[i - 2])
            + 2 * (1 - alpha1) * hp[i - 1]
            - (1 - alpha1) ** 2 * hp[i - 2]
        )

    a1 = math.exp(-1.414 * math.pi / lowpass_period)
    b1 = 2 * a1 * math.cos(1.414 * math.pi / lowpass_period)
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3

    filt = np.zeros(n)
    for i in range(2, n):
        filt[i] = c1 * (hp[i] + hp[i - 1]) / 2.0 + c2 * filt[i - 1] + c3 * filt[i - 2]

    return pd.Series(filt, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    highpass_period: int = 48,
    lowpass_period: int = 10,
    signal_window: int = 3,
    trend_window: int = 200,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    filt = _roofing_filter(close, highpass_period, lowpass_period)
    signal = filt.rolling(signal_window, min_periods=1).mean()
    trend_ema = close.ewm(span=trend_window, adjust=False).mean()
    trend_ok = close > trend_ema

    above = filt > signal
    cross_up = above & (~above.shift(1).fillna(False))
    cross_down = (~above) & above.shift(1).fillna(False)

    entry = cross_up & trend_ok.fillna(False)
    exit_signal = cross_down | (close < filt)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
    daily_ret = position.shift(1).fillna(0) * close.pct_change().fillna(0.0)
    return daily_ret
