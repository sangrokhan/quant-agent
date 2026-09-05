"""Strategy: Elder SafeZone Stop as trailing-exit mechanism on an EMA-trend
breakout entry (equity + crypto).

Hypothesis (knowledge_base/strategies_log.jsonl id=2026-09-06-118):
Dr. Alexander Elder's SafeZone Stop measures directional market "noise" as
the average recent counter-trend penetration (for longs: average of
max(previous_low - current_low, 0) over a lookback window), then places a
trailing stop `factor` multiples of that noise below the reference price
(close). Because it adapts to *counter-trend* penetration specifically
(not overall range like ATR), it should sit tighter than an ATR stop in
smooth trends and widen automatically in choppy/noisy ones, letting winners
run longer in clean trends while cutting losers faster in noisy ones. Per
https://pineify.app/algorithmic-trading/elder-safezone-stop ("estimates
directional market noise from recent counter-trend penetrations ... trailing
rule prevents the stop from loosening while the trend condition remains
active"). Tested here as the EXIT mechanism for a simple EMA-trend breakout
entry (long when close > trend EMA and price makes a new N-day high),
holding until the SafeZone trailing stop is hit or the trend EMA flips
bearish. First Elder SafeZone Stop strategy in this repo -- distinct from
all previously-tested Elder-family strategies (Elder-Ray Bull/Bear Power,
Elder Force Index, Elder Impulse System, Elder Triple Screen) since none of
those use a noise-adaptive trailing STOP as the exit rule; this is a
different mechanical construction (a dynamic risk-based exit, not an
oscillator entry signal).

Signal logic
------------
- Trend gate: close > EMA(trend_span) defines an active uptrend.
- Entry (long): trend gate is true AND close makes a new `breakout_window`
  -day high (breakout continuation entry into the trend).
- SafeZone noise: longNoise = rolling mean over `sz_lookback` bars of
  max(previous_low - current_low, 0) (only bars with downside penetration
  count; others contribute 0).
- SafeZone candidate stop = close - `sz_factor` * longNoise.
- One-way trailing rule: while in a position, the stop can only move UP
  (tighten), never down -- stop_t = max(stop_{t-1}, candidate_t).
- Exit: close crosses below the trailing SafeZone stop, OR the trend gate
  flips (close <= trend EMA), OR a `max_hold_days` time-stop.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    trend_span: int = 50,
    breakout_window: int = 20,
    sz_lookback: int = 10,
    sz_factor: float = 2.5,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]

    trend_ema = close.ewm(span=trend_span, adjust=False).mean()
    trend_up = close > trend_ema

    rolling_high = close.rolling(breakout_window).max()
    new_high = close >= rolling_high.shift(1).fillna(close)

    prev_low = low.shift(1)
    downside_penetration = (prev_low - low).clip(lower=0.0)
    long_noise = downside_penetration.rolling(sz_lookback).mean()

    candidate_stop = close - sz_factor * long_noise

    entry_signal = trend_up.fillna(False) & new_high.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    trailing_stop = None

    close_vals = close.values
    trend_up_vals = trend_up.fillna(False).values
    entry_vals = entry_signal.values
    cand_vals = candidate_stop.values
    n = len(close_vals)

    for i in range(n):
        if in_position:
            held = i - entry_idx
            stop_hit = trailing_stop is not None and close_vals[i] < trailing_stop
            trend_broke = not trend_up_vals[i]
            time_stop = held >= max_hold_days
            if stop_hit or trend_broke or time_stop:
                in_position = False
                trailing_stop = None
                position.iloc[i] = 0
                continue
            # one-way trail: only ratchet up
            if cand_vals[i] == cand_vals[i]:  # not NaN
                trailing_stop = cand_vals[i] if trailing_stop is None else max(trailing_stop, cand_vals[i])
            position.iloc[i] = 1
        else:
            if bool(entry_vals[i]):
                in_position = True
                entry_idx = i
                trailing_stop = cand_vals[i] if cand_vals[i] == cand_vals[i] else close_vals[i]
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    trend_span: int = 50,
    breakout_window: int = 20,
    sz_lookback: int = 10,
    sz_factor: float = 2.5,
    max_hold_days: int = 40,
) -> pd.Series:
    """Daily strategy returns (gross, no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        trend_span=trend_span,
        breakout_window=breakout_window,
        sz_lookback=sz_lookback,
        sz_factor=sz_factor,
        max_hold_days=max_hold_days,
    )

    daily_ret = close.pct_change().fillna(0.0)
    # Position at time t determines exposure to the return realized over
    # (t-1, t]; shift position by 1 to avoid look-ahead bias.
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
