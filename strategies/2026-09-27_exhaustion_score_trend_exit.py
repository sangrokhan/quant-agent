"""Strategy: Multi-dimensional trend-exhaustion EXIT overlay on a base
SMA trend-following long entry (daily-bar adaptation).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-XXX):
Per Draconic's "Exhaustion Detection Framework"
(https://draconic.ai/tradecraft/exhaustion-detection-framework, read via
browser_exec -- web_extract's ddgs backend is search-only), trend exhaustion
is detectable across THREE independent dimensions before price confirms a
reversal:
  1. Velocity deceleration: each swing's price-change-per-bar is smaller
     than the prior swing's (monotonic decline over the last few swings).
  2. Swing duration expansion: the current swing has run longer (in bars)
     than the session/trailing average swing duration.
  3. Combined statistical extremes: multiple independent metrics (velocity
     percentile, range percentile, swing-magnitude percentile) are
     simultaneously at/above a high percentile (>=90th) of their trailing
     distribution.
The source's own disclosed decision rule: score each dimension 0/1; 0/3 =
healthy trend (hold/enter), 1/3 = early warning (tighten stop), 2/3 =
"exhaustion likely, exit trend-following positions, do not enter new ones",
3/3 = "strong exhaustion, exit."

Adapted from the source's original intraday-session framing to this repo's
daily-bar OHLCV via a ZigZag-swing-point construction (percentage-deviation
pivots) computed on daily closes; "session" percentile is replaced with a
trailing rolling-window percentile (percentile_lookback bars) since there is
no intraday session boundary on daily bars.

Long-only, following this repo's SAFETY.md convention:
  - Enter long when close > SMA(trend_window) (established uptrend) AND the
    exhaustion score (computed on the CURRENT swing) is < entry_max_score
    (i.e. not already exhausted at the moment of entry).
  - Exit when the exhaustion score reaches >= exit_min_score (source's own
    "2 of 3 = exit" threshold) OR price closes back below SMA(trend_window)
    (baseline trend-break exit), whichever comes first.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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


def _zigzag_pivots(close: pd.Series, deviation_pct: float) -> np.ndarray:
    """Return an array of pivot indices (positions) via percentage-deviation
    ZigZag: a new pivot is confirmed once price reverses by >= deviation_pct
    from the last extreme."""
    n = len(close)
    close_v = close.values
    pivots = [0]
    direction = 0  # 0=undetermined, 1=up, -1=down
    last_extreme_idx = 0
    last_extreme_val = close_v[0]

    for i in range(1, n):
        price = close_v[i]
        if direction >= 0:
            if price > last_extreme_val:
                last_extreme_val = price
                last_extreme_idx = i
                direction = 1
            elif price <= last_extreme_val * (1 - deviation_pct):
                pivots.append(last_extreme_idx)
                direction = -1
                last_extreme_val = price
                last_extreme_idx = i
        if direction <= 0:
            if price < last_extreme_val or direction == 0:
                last_extreme_val = price
                last_extreme_idx = i
                if direction == 0:
                    continue
                direction = -1
            elif price >= last_extreme_val * (1 + deviation_pct):
                pivots.append(last_extreme_idx)
                direction = 1
                last_extreme_val = price
                last_extreme_idx = i
    pivots.append(n - 1)
    return np.array(sorted(set(pivots)))


def _exhaustion_score(
    df: pd.DataFrame,
    deviation_pct: float,
    percentile_lookback: int,
    extreme_pctl: float,
    velocity_swings_lookback: int = 3,
    duration_expansion_mult: float = 1.5,
) -> pd.Series:
    close = df["close"]
    high = df["high"]
    low = df["low"]
    n = len(close)

    pivots = _zigzag_pivots(close, deviation_pct)
    close_v = close.values

    # Per-bar "current swing" velocity (price change per bar since last pivot)
    # and duration (bars since last pivot).
    swing_id = np.zeros(n, dtype=int)
    for k in range(len(pivots) - 1):
        swing_id[pivots[k] : pivots[k + 1] + 1] = k

    velocity = np.full(n, np.nan)
    duration = np.full(n, np.nan)
    for i in range(n):
        p_idx = pivots[swing_id[i]]
        bars_since = i - p_idx
        duration[i] = bars_since
        if bars_since > 0:
            velocity[i] = abs(close_v[i] - close_v[p_idx]) / bars_since

    velocity_s = pd.Series(velocity, index=close.index)
    duration_s = pd.Series(duration, index=close.index)

    # Dimension 1: velocity deceleration -- compare each pivot's completed
    # swing velocity to the previous `velocity_swings_lookback` pivots' swing
    # velocities; decelerating if monotonically declining.
    swing_velocities = []
    for k in range(len(pivots) - 1):
        p0, p1 = pivots[k], pivots[k + 1]
        bars = p1 - p0
        v = abs(close_v[p1] - close_v[p0]) / bars if bars > 0 else 0.0
        swing_velocities.append(v)
    swing_velocities = np.array(swing_velocities)

    decel_by_swing = np.zeros(len(swing_velocities), dtype=bool)
    for k in range(velocity_swings_lookback, len(swing_velocities)):
        window = swing_velocities[k - velocity_swings_lookback : k + 1]
        decel_by_swing[k] = all(window[i] < window[i - 1] for i in range(1, len(window)))

    dim1 = np.zeros(n, dtype=bool)
    for i in range(n):
        k = swing_id[i]
        if k < len(decel_by_swing):
            dim1[i] = decel_by_swing[k]

    # Dimension 2: duration expansion -- current swing duration exceeds
    # duration_expansion_mult x trailing average completed-swing duration.
    swing_durations = np.diff(pivots)
    avg_duration_by_swing = np.full(len(swing_durations), np.nan)
    for k in range(1, len(swing_durations)):
        avg_duration_by_swing[k] = swing_durations[:k].mean()

    dim2 = np.zeros(n, dtype=bool)
    for i in range(n):
        k = swing_id[i]
        if k < len(avg_duration_by_swing) and not np.isnan(avg_duration_by_swing[k]):
            dim2[i] = duration[i] > (duration_expansion_mult * avg_duration_by_swing[k])

    # Dimension 3: combined statistical extremes -- velocity percentile AND
    # daily-range percentile AND swing-magnitude percentile, trailing rolling
    # window, count how many are >= extreme_pctl; extreme if >=2 of 3.
    daily_range = (high - low) / close.shift(1)
    velocity_pctl = velocity_s.rolling(percentile_lookback).apply(
        lambda x: (x < x.iloc[-1]).mean() if len(x.dropna()) > 1 else np.nan, raw=False
    )
    range_pctl = daily_range.rolling(percentile_lookback).apply(
        lambda x: (x < x.iloc[-1]).mean() if len(x.dropna()) > 1 else np.nan, raw=False
    )

    swing_magnitude = np.full(n, np.nan)
    for i in range(n):
        k = swing_id[i]
        p_idx = pivots[k]
        swing_magnitude[i] = abs(close_v[i] - close_v[p_idx])
    swing_magnitude_s = pd.Series(swing_magnitude, index=close.index)
    magnitude_pctl = swing_magnitude_s.rolling(percentile_lookback).apply(
        lambda x: (x < x.iloc[-1]).mean() if len(x.dropna()) > 1 else np.nan, raw=False
    )

    extreme_count = (
        (velocity_pctl >= extreme_pctl).astype(int)
        + (range_pctl >= extreme_pctl).astype(int)
        + (magnitude_pctl >= extreme_pctl).astype(int)
    )
    dim3 = extreme_count >= 2

    score = dim1.astype(int) + dim2.astype(int) + dim3.astype(int)
    return pd.Series(score, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 100,
    deviation_pct: float = 0.05,
    percentile_lookback: int = 60,
    extreme_pctl: float = 0.90,
    entry_max_score: int = 1,
    exit_min_score: int = 2,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(trend_window).mean()
    uptrend = close > sma

    score = _exhaustion_score(df, deviation_pct, percentile_lookback, extreme_pctl)

    n = len(close)
    state = np.zeros(n, dtype=int)
    uptrend_v = uptrend.values
    score_v = score.values

    in_position = False
    for i in range(n):
        if np.isnan(sma.values[i]):
            state[i] = 0
            continue
        if not in_position:
            if uptrend_v[i] and score_v[i] < entry_max_score:
                in_position = True
                state[i] = 1
            else:
                state[i] = 0
        else:
            if (not uptrend_v[i]) or score_v[i] >= exit_min_score:
                in_position = False
                state[i] = 0
            else:
                state[i] = 1

    signal = pd.Series(state, index=close.index).shift(1).fillna(0).astype(int)
    return signal


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 100,
    deviation_pct: float = 0.05,
    percentile_lookback: int = 60,
    extreme_pctl: float = 0.90,
    entry_max_score: int = 1,
    exit_min_score: int = 2,
) -> pd.Series:
    """Daily strategy returns, position-weighted, no transaction costs."""
    df = _prep(price_df)
    close = df["close"]
    positions = generate_signals(
        price_df,
        trend_window=trend_window,
        deviation_pct=deviation_pct,
        percentile_lookback=percentile_lookback,
        extreme_pctl=extreme_pctl,
        entry_max_score=entry_max_score,
        exit_min_score=exit_min_score,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = positions * daily_ret
    return strat_ret.fillna(0.0)
