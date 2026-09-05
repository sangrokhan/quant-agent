"""Strategy: Gator Oscillator (Bill Williams) awakening-trend entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-050):
The Gator Oscillator is a dual histogram built from the same three
Alligator SMMA lines (Jaw=13, Teeth=8, Lips=5, all forward-shifted per
Williams' convention) that tracks |Jaw-Teeth| (upper bars) and
|Teeth-Lips| (lower bars). Per QuantifiedStrategies.com's Gator Oscillator
article (https://www.quantifiedstrategies.com/gator-oscillator/): both
histogram bars flipping from contracting (red, gap narrowing -- "Alligator
asleep") to simultaneously expanding (green, gap widening -- "Alligator
opening its mouth to eat") signals a fresh trend starting. This strategy
enters long when BOTH gaps turn green (expanding) on the same bar for the
first time after having both been red, filtered by Lips > Teeth > Jaw
(bullish line ordering) to pick the trend direction; exits when either
gap turns red again (contracting -- "Alligator closing its mouth") or a
max_hold_days time-stop. This is distinct from the already-tested/accepted
Alligator Lips-crosses-above-both-lines strategy (2026-09-04-112), which
triggers on a lips crossover rather than the Gator's gap-expansion state
change.

Signal logic
------------
- Alligator lines: Jaw = SMMA(13) of median price shifted 8 bars forward,
  Teeth = SMMA(8) shifted 5, Lips = SMMA(5) shifted 3 (Williams' standard
  Fibonacci periods/shifts).
- Upper Gator bar = |Jaw - Teeth|; lower Gator bar = |Teeth - Lips|.
- A bar is "green" (expanding) when it is larger than the previous bar of
  the same series, "red" (contracting) otherwise.
- Entry (long): upper bar AND lower bar are BOTH green on the same day,
  immediately following a day where at least one of them was red (i.e.
  the "wake up" transition, not every day both happen to be green), AND
  Lips > Teeth > Jaw (bullish fan ordering, picks direction).
- Exit: upper bar turns red OR lower bar turns red (mouth closing), or a
  max_hold_days time-stop (source gives no explicit stop rule, matching
  the convention used for the related Alligator strategy).
- Flat (no position) at all other times.

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

    upper_bar = (jaw - teeth).abs()
    lower_bar = (teeth - lips).abs()

    upper_green = upper_bar > upper_bar.shift(1)
    lower_green = lower_bar > lower_bar.shift(1)

    both_green_now = upper_green & lower_green
    both_green_prev = both_green_now.shift(1).fillna(False)
    wake_up = both_green_now & (~both_green_prev)

    bullish_order = (lips > teeth) & (teeth > jaw)

    entry = wake_up & bullish_order
    exit_signal = (~upper_green) | (~lower_green)

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
            if bool(exit_signal.iloc[i]) or hold_count >= max_hold_days:
                in_pos = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    """Position-weighted daily returns (no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **params)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
