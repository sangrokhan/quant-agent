"""Strategy: ADX/DMI directional crossover + ADX-RISING-SLOPE confirmation.

Hypothesis (knowledge_base id=2026-09-11-097):
Source: https://quantstock.org/blog/adx-indicator-trading-strategy (visited
this iteration, useful=true). Source's disclosed "Bullish Setup" rule
adds a step beyond the plain static-threshold DI-crossover already tested
and rejected in this repo (2026-09-03-017):
  1. Wait for +DI to cross above -DI.
  2. Confirm ADX is above 20 (preferably above 25).
  3. "Enter long when ADX IS RISING, confirming the uptrend is
     strengthening" -- an explicit slope condition, not merely a static
     level gate.

2026-09-03-017 was rejected specifically because of catastrophic parameter
sensitivity to the exact static adx_threshold chosen (Sharpe decayed
monotonically from 0.96 at threshold=15 to 0.17 at threshold=30 on QQQ,
rel.std 0.53 > the 0.5 ceiling) -- i.e. the edge was fragile to *where you
draw the ADX cutoff line*, not a stable property of the signal. This
iteration's hypothesis is a direct, source-grounded fix: replace/augment
the static-level gate with a SLOPE condition (ADX today > ADX
adx_slope_lookback days ago), which is qualitatively different from "is ADX
above X" and should be much less sensitive to the exact threshold value
since it's a relative/directional comparison rather than an absolute cutoff.
We keep a much looser static floor (adx_floor, default 15, well below the
prior study's most-sensitive high end) purely to exclude dead-flat/near-zero
ADX readings, and rely primarily on the rising-slope condition for the real
trend-strength confirmation.

Signal logic (long-only, per SAFETY.md)
------------
- +DI, -DI, ADX computed per Wilder's standard DMI formulas (period).
- Entry (long): +DI crosses above -DI (bull_cross) AND ADX > adx_floor AND
  ADX(t) > ADX(t - adx_slope_lookback) (ADX is rising over the lookback
  window, confirming strengthening trend per source's stated rule).
- Exit: -DI crosses above +DI (bear_cross), OR ADX turns down (ADX(t) <
  ADX(t - adx_slope_lookback)) while still in position, OR a
  max_hold_days time-stop backstop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _wilder_smooth(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def _dmi_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int):
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(0.0, index=high.index)
    minus_dm = pd.Series(0.0, index=high.index)
    plus_dm[(up_move > down_move) & (up_move > 0)] = up_move[(up_move > down_move) & (up_move > 0)]
    minus_dm[(down_move > up_move) & (down_move > 0)] = down_move[(down_move > up_move) & (down_move > 0)]

    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)

    atr = _wilder_smooth(tr, period)
    plus_dm_smooth = _wilder_smooth(plus_dm, period)
    minus_dm_smooth = _wilder_smooth(minus_dm, period)

    plus_di = 100.0 * (plus_dm_smooth / atr.replace(0, pd.NA))
    minus_di = 100.0 * (minus_dm_smooth / atr.replace(0, pd.NA))

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)
    adx = _wilder_smooth(dx.fillna(0.0), period)

    return plus_di, minus_di, adx


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 14,
    adx_floor: float = 15.0,
    adx_slope_lookback: int = 5,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    plus_di, minus_di, adx = _dmi_adx(high, low, close, period)

    plus_above = plus_di > minus_di
    prev_plus_above = plus_above.shift(1).fillna(False)
    bull_cross = plus_above & (~prev_plus_above)
    bear_cross = (~plus_above) & prev_plus_above

    adx_rising = adx > adx.shift(adx_slope_lookback)
    adx_falling = adx < adx.shift(adx_slope_lookback)

    entry = bull_cross & (adx > adx_floor) & adx_rising
    exit_signal = bear_cross | adx_falling

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    entry_arr = entry.to_numpy()
    exit_arr = exit_signal.to_numpy()
    pos_arr = position.to_numpy().copy()

    for i in range(len(df)):
        if in_pos:
            hold_count += 1
            if exit_arr[i] or hold_count >= max_hold_days:
                in_pos = False
                hold_count = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if entry_arr[i]:
                in_pos = True
                hold_count = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    position = pd.Series(pos_arr, index=df.index, dtype=int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    period: int = 14,
    adx_floor: float = 15.0,
    adx_slope_lookback: int = 5,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return daily strategy returns (position lagged by 1 bar to avoid lookahead)."""
    df = _prep(price_df)
    position = generate_signals(
        df,
        period=period,
        adx_floor=adx_floor,
        adx_slope_lookback=adx_slope_lookback,
        max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(float) * daily_returns
    return strat_returns
