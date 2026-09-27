"""Strategy: ROC-of-ROC acceleration-agreement trend continuation (long-only).

Hypothesis (source: https://www.luxalgo.com/library/indicator/roc-of-roc/,
read 2026-09-28 via browser_exec while browsing LuxAlgo's indicator library
for a fresh angle -- found via the same listing scroll that surfaced this
trigger's other LuxAlgo-sourced strategies; 0 prior hits confirmed via
strategies_index.jsonl before implementation):

LuxAlgo's "ROC-of-ROC" plots the acceleration of price: a
`velocity_length`-bar percent rate of change (velocity) DIFFERENCED again
(not percent-changed -- source explicitly built it this way: "the
definitive clean build of ROC-of-ROC takes the second pass as a
difference rather than a percent change") over `acceleration_length` bars,
smoothed. Source's own disclosed trading interpretation: "Velocity
context: read the acceleration sign against the velocity line; agreement
is thrust, a split is the early warning" -- i.e. velocity positive AND
acceleration positive together (both derivatives agreeing) signals a
genuinely strengthening (not just ongoing) uptrend, "thrust." A split
(velocity positive but acceleration negative) is "an advance still rising
but losing thrust" -- the source's own explicit early-warning/tighten-risk
signal, not an automatic reversal call, but informative for an exit.

We operationalize "thrust" as the long entry trigger (fresh agreement:
both velocity and acceleration turn/stay positive together) within an
SMA(trend_window) uptrend gate (repo convention, since ROC-of-ROC itself
measures magnitude of momentum change, not absolute trend direction
robustly enough alone); exit on the source's own "deceleration warning"
(velocity positive, acceeleration turns negative -- thrust fading) OR the
trend filter breaking OR a max_hold_days time-stop.

First "ROC-of-ROC" / second-derivative-momentum strategy in this repo (0
prior hits for "ROC-of-ROC"/"ROC of ROC" in strategies_index.jsonl) --
distinct from this repo's many first-derivative ROC/momentum strategies
(plain ROC threshold crossings, RSI, TSI, etc.) which only look at
velocity, never at velocity's own rate of change.

Signal logic
------------
- velocity = close.pct_change(velocity_length) * 100 (standard % ROC).
- acceleration_raw = velocity.diff(acceleration_length) (a DIFFERENCE, per
  source's explicit "second pass as a difference" construction, not
  another percent-change).
- acceleration = SMA(acceleration_raw, acceleration_smoothing).
- Entry (long): fresh "thrust" agreement -- velocity > 0 AND acceleration
  crosses from <= 0 up through > 0 (acceleration zero-cross while velocity
  already positive) AND close > SMA(trend_window).
- Exit: "deceleration warning" -- velocity > 0 AND acceleration crosses
  from > 0 down through <= 0 (source's own disclosed early-warning state),
  OR close < SMA(trend_window) (trend filter breaks), OR max_hold_days
  time-stop.

Interface contract (see validation/validators.py and validation/grid_test.py):
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


def _roc_of_roc(
    close: pd.Series, velocity_length: int, acceleration_length: int, acceleration_smoothing: int
):
    velocity = close.pct_change(velocity_length) * 100.0
    acceleration_raw = velocity.diff(acceleration_length)
    acceleration = acceleration_raw.rolling(acceleration_smoothing).mean()
    return velocity, acceleration


def generate_signals(
    price_df: pd.DataFrame,
    velocity_length: int = 9,
    acceleration_length: int = 9,
    acceleration_smoothing: int = 3,
    trend_window: int = 50,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    sma = close.rolling(trend_window).mean()
    trend_ok = close > sma

    velocity, acceleration = _roc_of_roc(
        close, velocity_length, acceleration_length, acceleration_smoothing
    )

    accel_positive = acceleration > 0
    fresh_accel_up = accel_positive & (~accel_positive.shift(1).fillna(False))
    thrust_entry = fresh_accel_up & (velocity > 0) & trend_ok

    accel_negative_from_positive = (~accel_positive) & (accel_positive.shift(1).fillna(False))
    deceleration_warning = accel_negative_from_positive & (velocity > 0)

    n = len(df)
    trend_ok_arr = trend_ok.to_numpy()
    thrust_entry_arr = thrust_entry.to_numpy()
    decel_arr = deceleration_warning.to_numpy()

    pos = pd.Series(0.0, index=df.index)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_now = (
                not bool(trend_ok_arr[i])
                or bool(decel_arr[i])
                or hold_count >= max_hold_days
            )
            if exit_now:
                in_pos = False
                hold_count = 0
            else:
                pos.iloc[i] = 1.0
        if not in_pos and bool(thrust_entry_arr[i]):
            in_pos = True
            hold_count = 0
            pos.iloc[i] = 1.0

    return pos


def generate_returns(
    price_df: pd.DataFrame,
    velocity_length: int = 9,
    acceleration_length: int = 9,
    acceleration_smoothing: int = 3,
    trend_window: int = 50,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return the daily strategy return series (no transaction costs)."""
    df = _prep(price_df)
    pos = generate_signals(
        df,
        velocity_length=velocity_length,
        acceleration_length=acceleration_length,
        acceleration_smoothing=acceleration_smoothing,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0.0)
    return strat_ret
