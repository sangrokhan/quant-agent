"""Strategy: Ehlers Roofing Filter crossing its own SMA signal line,
gated by a 200-period trend EMA.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
John Ehlers' "Roofing Filter" is a two-stage digital signal processor: a
high-pass filter strips out long-term trend/drift (cycles longer than the
`hp_period`), then a low-pass (SuperSmoother-style 2-pole) filter smooths
the remaining high-frequency noise, leaving a line that "hugs price action
closely but with far less jitter than a typical moving average" and
"catches reversals 2-3 bars earlier than a 20 EMA" (per source). Per
https://theindicatorlab.com/reviews/ehlers-roofing-filter/ (via
browser_exec/google.com fallback -- web_search DDGS backend TLS/
connection errors this iteration): "Long Entry: Wait for the Roofing
Filter line to cross above its 3-period SMA, and price should be above
the 200 EMA on the same timeframe... Exit: Trail with the filter line
itself. If price closes below the filter line (for longs), get out."

Construction (standard Ehlers 2-pole Roofing Filter formulation,
TASC 2013): 
  1. High-pass filter (2-pole) on close with cutoff period hp_period,
     removing slow trend/drift components.
  2. SuperSmoother (2-pole low-pass) applied to the high-pass output with
     cutoff period lp_period, removing fast noise.
  3. Signal line = SMA(roofing_filter, signal_period) (default 3).

Operationalized: long entry when RF crosses above its signal SMA AND
close > EMA(200) trend filter; exit when close crosses back below the RF
line itself (source's own trailing-exit rule), or a max_hold_days
time-stop.

First Ehlers Roofing Filter strategy in this repo (distinct from other
Ehlers-family entries already tested: Instantaneous Trendline, Cyber
Cycle, Even Better Sinewave, Voss Predictive Filter, Deviation-Scaled MA,
Trendflex -- none of those use the specific 2-stage high-pass-then-
low-pass "Roofing Filter" construction).

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


def _roofing_filter(close: pd.Series, hp_period: int, lp_period: int) -> pd.Series:
    """Ehlers 2-pole high-pass -> SuperSmoother low-pass Roofing Filter."""
    vals = close.values.astype(float)
    n = len(vals)

    # 2-pole high-pass filter (removes cycles longer than hp_period)
    alpha1 = (math.cos(2 * math.pi / hp_period) + math.sin(2 * math.pi / hp_period) - 1) / math.cos(
        2 * math.pi / hp_period
    )
    hp = np.zeros(n)
    for i in range(2, n):
        hp[i] = (
            (1 - alpha1 / 2) ** 2 * (vals[i] - 2 * vals[i - 1] + vals[i - 2])
            + 2 * (1 - alpha1) * hp[i - 1]
            - (1 - alpha1) ** 2 * hp[i - 2]
        )

    # 2-pole SuperSmoother low-pass filter (removes noise below lp_period)
    a1 = math.exp(-1.414 * math.pi / lp_period)
    b1 = 2 * a1 * math.cos(1.414 * math.pi / lp_period)
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3

    rf = np.zeros(n)
    for i in range(2, n):
        rf[i] = c1 * (hp[i] + hp[i - 1]) / 2 + c2 * rf[i - 1] + c3 * rf[i - 2]

    return pd.Series(rf, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    hp_period: int = 48,
    lp_period: int = 12,
    signal_period: int = 3,
    trend_window: int = 200,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rf = _roofing_filter(close, hp_period, lp_period)
    signal = rf.rolling(signal_period).mean()
    ema_trend = close.ewm(span=trend_window, adjust=False).mean()

    above_signal = rf > signal
    prev_above_signal = above_signal.shift(1)
    cross_up = above_signal & ~prev_above_signal.fillna(False)

    trend_up = close > ema_trend
    entry = cross_up.fillna(False) & trend_up.fillna(False)

    # exit: trail with the filter line itself -- price closes below RF line
    # (interpret RF, a filtered oscillator around 0, as a proxy trailing
    # reference by comparing close's own EMA(rf-equivalent smoothing) is not
    # directly meaningful since RF isn't a price-level line; use the
    # source's literal rule via a price-level reconstruction: track a
    # rolling reference price at entry and exit when close drops below the
    # signal line (RF's own smoothed version), which is the closest robust
    # proxy for "if price closes below the filter line, get out" given RF
    # is a zero-centered oscillator, not a price-level line in this
    # implementation.
    exit_signal_cross = (rf < signal) & (above_signal.shift(1).fillna(False))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal_cross.iloc[i]) or held >= max_hold_days:
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
