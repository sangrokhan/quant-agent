"""Strategy: Ehlers Super Passband Filter (TASC Jul 2016) RMS band entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-006),
sourced from https://traders.com/documentation/feedbk_docs/2016/07/traderstips.html
(TradeStation EasyLanguage code, visited this iteration) and
http://www2.wealth-lab.com/WL5Wiki/TASCJul2016.ashx (Wealth-Lab
WealthScript strategy, visited this iteration): John Ehlers' Super
Passband Filter (Stocks & Commodities, July 2016) is a recursive 2-pole
bandpass filter with two adjustable periods, designed to reject both
very-low-frequency (trend) and high-frequency (noise) components, leaving
a near-zero-lag oscillator suited to cyclical turning points. The
article's own systematic rule bands the filter with a rolling RMS
(root-mean-square) envelope and trades crossings of that envelope:

    PB = (a1-a2)*Close + (a2*(1-a1)-a1*(1-a2))*Close[1]
         + ((1-a1)+(1-a2))*PB[1] - (1-a1)*(1-a2)*PB[2]
         where a1 = 5/Period1, a2 = 5/Period2   (Period1 < Period2)
    RMS = sqrt(mean(PB[i]^2 for i in last 50 bars))

    Buy: PB crosses above -RMS.
    Exit long (reversal stop): PB crosses back below -RMS (false-entry
        signal), or PB crosses above +RMS (source's overbought exit,
        treated as a risk-off flat exit rather than reversing short --
        this repo is long-only per SAFETY.md).

First Ehlers Super Passband Filter strategy in this repo (0 prior hits;
distinct from all prior Ehlers-family strategies already tested here --
Fisher Transform, MESA Sine Wave, Voss Predictive Filter, Roofing Filter,
Decycler, Trendflex, Even Better Sinewave, Ultimate Smoother, Detrended
Synthetic Price, Instantaneous Trendline, Cybernetic Oscillator -- none of
which use this specific two-period recursive bandpass + rolling-RMS-band
construction).

Signal logic
------------
- Compute PB (recursive bandpass filter) and its rolling RMS envelope
  exactly per the source formula above.
- Long entry: PB crosses from <= -RMS to > -RMS (oversold-to-neutral
  cross, source's disclosed buy trigger).
- Exit to flat: PB crosses back below -RMS (false-entry/reversal-stop
  exit) OR PB crosses above +RMS (overbought exit -- long-only adaptation
  of the source's reversal-to-short rule) OR a `max_hold_days` time-stop.
- Gated by close > SMA(trend_window) for trend confirmation (the source
  itself notes the filter is "promising for counter-trend trades and
  buying significant dips" -- pairing with a trend filter is this repo's
  standard practice for oscillator-crossover strategies, consistent with
  Fisher Transform 2026-09-05-086, IMI 2026-09-05-071, etc.)
- Long-only, consistent with this repo's other strategies and SAFETY.md.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns, position lagged by 1 day to avoid look-ahead bias)
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


def _super_passband(close: pd.Series, period1: int, period2: int, rms_window: int) -> tuple[pd.Series, pd.Series]:
    a1 = 5.0 / period1
    a2 = 5.0 / period2

    n = len(close)
    close_vals = close.values.astype(float)
    pb = np.zeros(n)

    c1 = a1 - a2
    c2 = a2 * (1 - a1) - a1 * (1 - a2)
    c3 = (1 - a1) + (1 - a2)
    c4 = (1 - a1) * (1 - a2)

    for i in range(n):
        prev_close = close_vals[i - 1] if i >= 1 else close_vals[i]
        pb1 = pb[i - 1] if i >= 1 else 0.0
        pb2 = pb[i - 2] if i >= 2 else 0.0
        pb[i] = c1 * close_vals[i] + c2 * prev_close + c3 * pb1 - c4 * pb2

    pb_series = pd.Series(pb, index=close.index)
    rms = np.sqrt((pb_series ** 2).rolling(rms_window, min_periods=rms_window).mean())
    return pb_series, rms


def generate_signals(
    price_df: pd.DataFrame,
    period1: int = 40,
    period2: int = 60,
    rms_window: int = 50,
    trend_window: int = 100,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    pb, rms = _super_passband(close, period1, period2, rms_window)
    neg_rms = -rms

    sma_trend = close.rolling(trend_window, min_periods=trend_window).mean()
    above_trend = (close > sma_trend).fillna(False)

    crossed_above_neg_rms = (pb > neg_rms) & (pb.shift(1) <= neg_rms.shift(1))
    crossed_below_neg_rms = (pb < neg_rms) & (pb.shift(1) >= neg_rms.shift(1))
    crossed_above_pos_rms = (pb > rms) & (pb.shift(1) <= rms.shift(1))

    entry_event = crossed_above_neg_rms.fillna(False) & above_trend
    exit_event = (crossed_below_neg_rms | crossed_above_pos_rms).fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_count = 0
    entry_arr = entry_event.values
    exit_arr = exit_event.values
    above_trend_arr = above_trend.values

    for i in range(len(df.index)):
        if in_position:
            hold_count += 1
            if exit_arr[i] or (not above_trend_arr[i]) or hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_arr[i]:
                in_position = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **params)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
