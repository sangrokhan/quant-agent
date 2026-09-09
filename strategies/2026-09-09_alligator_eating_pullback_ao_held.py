"""Strategy: Williams Alligator "Eating" pullback entry, Awesome Oscillator
momentum-held confirmation (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-071):
Per NexusFi Academy's "Williams Alligator and Awesome Oscillator" guide
(https://nexusfi.com/a/indicators/williams-alligator-awesome-oscillator,
browser_exec fallback -- web_search DDGS returned no results/errored for
several direct queries; most of the article is paywalled beyond the
Overview/Components/Fractals sections), the disclosed pullback-entry
approach (quoted from a forum practitioner, framed as the "most
experienced Alligator traders prefer" method) is: in an Alligator "Eating"
uptrend (Lips > Teeth > Jaw, all diverging), wait for price to pull back
toward the Lips or Teeth line, then enter when price shows rejection and
closes back in the trend direction, WHILE the Awesome Oscillator remains
positive and has NOT crossed zero during the pullback (momentum never
actually flipped negative, confirming the pullback is shallow/healthy
rather than a trend change). This combines two indicators already present
individually in this repo (2026-09-04 Alligator fanout, 2026-09-04 Awesome
Oscillator zeroline) via a rule neither existing strategy implements
(pullback-to-Alligator-line entry gated by AO staying positive throughout
the pullback, not just an AO zero-cross or Alligator fanout alone).

Signal logic
------------
- Alligator: SMMA(median_price, 13) shifted forward 8 bars = Jaw,
  SMMA(median_price, 8) shifted forward 5 bars = Teeth, SMMA(median_price,
  5) shifted forward 3 bars = Lips (median_price = (high+low)/2). SMMA
  approximated here by an EWM with alpha=1/period (Wilder-style smoothing,
  the standard SMMA construction).
- Eating/uptrend gate: lips > teeth > jaw (all three properly ordered).
- Pullback: close dips to within `pullback_band_pct` of the teeth line
  (close between teeth*(1-pullback_band_pct) and lips) within the last
  `pullback_lookback` bars.
- AO (Awesome Oscillator) = SMA(median_price, 5) - SMA(median_price, 34).
  AO-held-positive filter: AO has stayed > 0 for the entire pullback
  window (no zero-cross during the dip).
- Rejection/entry trigger: close > close.shift(1) (bullish rejection
  candle proxy on daily bars) on the bar the pullback + AO-held conditions
  are satisfied.
- Entry (long): eating gate AND recent pullback-to-band AND AO held
  positive throughout AND today's rejection candle.
- Exit: lips crosses back below teeth (Eating state breaks), OR AO crosses
  below zero, OR a `max_hold_days` time-stop (source discusses fractal-
  based stops which aren't reproducible on daily OHLC without intrabar
  data; this repo substitutes a time-stop per its consistent convention).
- Flat otherwise; long-only, no shorting (per SAFETY.md).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly across a parameter grid).
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
    return series.ewm(alpha=1.0 / period, adjust=False).mean()


def generate_signals(
    price_df: pd.DataFrame,
    jaw_period: int = 13,
    jaw_offset: int = 8,
    teeth_period: int = 8,
    teeth_offset: int = 5,
    lips_period: int = 5,
    lips_offset: int = 3,
    ao_fast: int = 5,
    ao_slow: int = 34,
    pullback_lookback: int = 5,
    pullback_band_pct: float = 0.02,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    median_price = (df["high"] + df["low"]) / 2.0

    jaw = _smma(median_price, jaw_period).shift(jaw_offset)
    teeth = _smma(median_price, teeth_period).shift(teeth_offset)
    lips = _smma(median_price, lips_period).shift(lips_offset)

    eating_up = (lips > teeth) & (teeth > jaw)

    ao = median_price.rolling(ao_fast).mean() - median_price.rolling(ao_slow).mean()
    ao_positive = ao > 0
    ao_held_positive = ao_positive.rolling(pullback_lookback, min_periods=pullback_lookback).min().astype(bool)

    band_low = teeth * (1.0 - pullback_band_pct)
    in_band = (close <= lips) & (close >= band_low)
    touched_band_recently = in_band.rolling(pullback_lookback, min_periods=1).max().astype(bool)

    rejection_candle = close > close.shift(1)

    entry = (
        eating_up.fillna(False)
        & touched_band_recently.fillna(False)
        & ao_held_positive.fillna(False)
        & rejection_candle.fillna(False)
    )

    exit_eating_break = lips < teeth
    exit_ao_negative = ao < 0

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_eating_break.iloc[i]) or bool(exit_ao_negative.iloc[i]) or held >= max_hold_days:
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
