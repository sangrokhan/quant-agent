"""Strategy: Williams Alligator (Bill Williams, 1995) crossover/fan-out.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-112):
Three forward-shifted smoothed moving averages (SMMA) -- Jaw (13, shift 8),
Teeth (8, shift 5), Lips (5, shift 3), all Fibonacci periods -- track a
trend's "awake" (lines fanned apart in order lips>teeth>jaw for an uptrend)
vs "asleep" (lines tangled/close together, range-bound, ignore) state. A
long entry fires when the Lips line crosses above BOTH Teeth and Jaw (the
alligator "waking up" and starting to fan bullishly); exit when Lips
crosses back below either Teeth or Jaw (fan collapsing / alligator closing
its mouth), or after max_hold_days as a safety time-stop since the source
article gives no explicit stop-loss/take-profit rule of its own.

Per https://howtotrade.com/indicators/alligator-indicator/ (crossover
strategy section): "exit your buy positions when the lip of the alligator
crosses the teeth and the jaw to the bottom side."

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _smma(series: pd.Series, period: int) -> pd.Series:
    """Wilder/Williams smoothed moving average: seed with SMA(period), then
    smma[t] = (smma[t-1]*(period-1) + price[t]) / period."""
    smma = series.copy() * float("nan")
    sma_seed = series.rolling(period).mean()
    seeded = False
    vals = series.values
    out = [float("nan")] * len(series)
    for i in range(len(series)):
        if not seeded:
            if i >= period - 1:
                out[i] = sma_seed.iloc[i]
                seeded = True
        else:
            out[i] = (out[i - 1] * (period - 1) + vals[i]) / period
    return pd.Series(out, index=series.index)


def _alligator_lines(
    df: pd.DataFrame,
    jaw_period: int,
    jaw_shift: int,
    teeth_period: int,
    teeth_shift: int,
    lips_period: int,
    lips_shift: int,
):
    median_price = (df["high"] + df["low"]) / 2.0
    jaw = _smma(median_price, jaw_period).shift(jaw_shift)
    teeth = _smma(median_price, teeth_period).shift(teeth_shift)
    lips = _smma(median_price, lips_period).shift(lips_shift)
    return jaw, teeth, lips


def generate_signals(
    price_df: pd.DataFrame,
    jaw_period: int = 13,
    jaw_shift: int = 8,
    teeth_period: int = 8,
    teeth_shift: int = 5,
    lips_period: int = 5,
    lips_shift: int = 3,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    jaw, teeth, lips = _alligator_lines(
        df, jaw_period, jaw_shift, teeth_period, teeth_shift, lips_period, lips_shift
    )

    lips_above_both = (lips > teeth) & (lips > jaw)
    lips_below_either = (lips < teeth) | (lips < jaw)
    lips_above_both_prev = lips_above_both.shift(1).fillna(False)

    entry = lips_above_both & (~lips_above_both_prev)
    exit_signal = lips_below_either

    valid = jaw.notna() & teeth.notna() & lips.notna()

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(len(df)):
        if not valid.iloc[i]:
            position.iloc[i] = 0
            continue
        if in_pos:
            hold_count += 1
            if exit_signal.iloc[i] or hold_count >= max_hold_days:
                in_pos = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if entry.iloc[i]:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    jaw_period: int = 13,
    jaw_shift: int = 8,
    teeth_period: int = 8,
    teeth_shift: int = 5,
    lips_period: int = 5,
    lips_shift: int = 3,
    max_hold_days: int = 20,
) -> pd.Series:
    """Daily strategy returns: yesterday's position times today's close-close return."""
    df = _prep(price_df)
    position = generate_signals(
        df,
        jaw_period=jaw_period,
        jaw_shift=jaw_shift,
        teeth_period=teeth_period,
        teeth_shift=teeth_shift,
        lips_period=lips_period,
        lips_shift=lips_shift,
        max_hold_days=max_hold_days,
    )
    price_returns = df["close"].pct_change()
    strat_returns = position.shift(1).fillna(0) * price_returns
    return strat_returns.fillna(0.0)
