"""Strategy: Ehlers Voss Predictive Filter crossover (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl):
John Ehlers' "Voss Predictive Filter" (TASC Aug 2019, "A Peek Into the
Future") applies a narrow bandpass filter to price (`Filt`), then computes a
negative-group-delay "predictor" line (`Voss`) as a weighted moving average
of past Voss values, subtracted from a scaled Filt -- designed to lead Filt
at cyclical turning points rather than lag it, per Ehlers' own derivation
from Henning U. Voss's negative-delay filter theory. Per ATAS's trading-
rules writeup of the indicator: "Bullish crossing. If the [Voss] line
crosses the [Filt] line upward, it is a buying signal. Bearish crossing...
downward, it is a selling signal." We operationalize this as: long entry
when Voss crosses above Filt; exit when Voss crosses back below Filt, or a
max_hold_days time-stop (added since Ehlers' own indicator has no explicit
stop and ATAS's own backtest reported frequent whipsaw losses on tick data,
suggesting a time-stop is a reasonable robustness addition for a daily-bar
adaptation).

Source: https://www.prorealcode.com/prorealtime-indicators/voss-predictive-filter-vpf/
(exact recursive formula/code); trading rule per
https://atas.net/blog/voss-predictive-filter/ (Voss/Filt crossover =
buy/sell signal, tested on intraday ES/SPY data by the source with mixed
but net-positive results).

First Ehlers Voss Predictive Filter strategy in this repo -- distinct from
all other Ehlers-family strategies already tested (Fisher Transform,
Inverse Fisher Transform of Stochastic, Even Better Sinewave, MESA Sine
Wave, Roofing Filter, Instantaneous Trendline) since Voss is a purely
recursive negative-group-delay PREDICTOR line crossed against its own
bandpass input, not an oscillator threshold/zero-cross or a dual-line
sine/lead-sine pair.

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


def _voss_filter(
    close: pd.Series, period: int, predict: int, bandwidth: float
) -> tuple[pd.Series, pd.Series]:
    """Compute Ehlers' Voss Predictive Filter (Filt, Voss) per the
    canonical recursive formula (ProRealCode / TASC Aug 2019)."""
    n = len(close)
    c = close.to_numpy(dtype=float)

    order = 3 * predict
    f1 = math.cos(2 * math.pi / period)
    g1 = math.cos(bandwidth * 2 * math.pi / period)
    s1 = 1.0 / g1 - math.sqrt(1.0 / (g1 * g1) - 1.0)

    filt = np.zeros(n)
    voss = np.zeros(n)

    for i in range(n):
        if i <= 5:
            filt[i] = 0.0
            voss[i] = 0.0
            continue
        c_im2 = c[i - 2] if i >= 2 else c[0]
        filt[i] = (
            0.5 * (1 - s1) * (c[i] - c_im2)
            + f1 * (1 + s1) * filt[i - 1]
            - s1 * filt[i - 2]
        )
        sumc = 0.0
        for count in range(order):
            idx = i - (order - count)
            if idx >= 0:
                sumc += ((count + 1) / order) * voss[idx]
        voss[i] = ((3 + order) / 2.0) * filt[i] - sumc

    return pd.Series(filt, index=close.index, name="filt"), pd.Series(
        voss, index=close.index, name="voss"
    )


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 20,
    predict: int = 3,
    bandwidth: float = 0.25,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    filt, voss = _voss_filter(close, period, predict, bandwidth)

    long_trigger = (voss > filt) & (voss.shift(1) <= filt.shift(1))
    exit_trigger = (voss < filt) & (voss.shift(1) >= filt.shift(1))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trigger.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(long_trigger.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1

    position.name = "position"
    return position


def generate_returns(
    price_df: pd.DataFrame,
    period: int = 20,
    predict: int = 3,
    bandwidth: float = 0.25,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    position = generate_signals(
        df,
        period=period,
        predict=predict,
        bandwidth=bandwidth,
        max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns.name = "strategy_returns"
    return strat_returns
