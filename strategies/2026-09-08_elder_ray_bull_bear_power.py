"""Strategy: Elder Ray Index (Bull Power / Bear Power) trend-following entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-007):
Per https://www.daytrading.com/elder-ray-index (Dr. Alexander Elder's Elder
Ray Index): Bull Power = Daily High - EMA(n); Bear Power = Daily Low -
EMA(n). A long entry signal fires when (1) Bear Power is negative but
increasing (selling pressure fading) AND (2) Bull Power is increasing
(buying pressure strengthening) -- "inherently trend-following" per the
source. The source also recommends confirming with the EMA's own slope
(positive slope favors long trades) -- we add that as a trend filter for
the long-only adaptation required by SAFETY.md. Exit when the entry
condition reverses (Bear Power turns decreasing, or Bull Power turns
decreasing while positive -- the source's own mirrored short-entry
condition, repurposed here as an exit rather than a short) or a
max_hold_days time-stop. First Elder Ray Index strategy in this repo.

Signal logic
------------
- EMA(n) of close.
- Bull Power = high - EMA; Bear Power = low - EMA.
- Trend filter: EMA is rising (EMA > EMA shifted by ema_slope_lookback bars).
- Entry (long): Bear Power < 0 AND Bear Power is increasing (today's Bear
  Power > yesterday's) AND Bull Power is increasing (today's > yesterday's)
  AND trend filter (EMA rising).
- Exit: Bear Power stops increasing (today's <= yesterday's), OR Bull Power
  stops increasing while positive (source's mirrored short-entry condition:
  Bull Power positive but decreasing AND Bear Power decreasing), OR trend
  filter breaks (EMA no longer rising), OR max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series   ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
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
    ema_period: int = 21,
    ema_slope_lookback: int = 5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    ema = close.ewm(span=ema_period, adjust=False, min_periods=ema_period).mean()
    bull_power = high - ema
    bear_power = low - ema

    ema_rising = ema > ema.shift(ema_slope_lookback)

    bear_increasing = bear_power > bear_power.shift(1)
    bull_increasing = bull_power > bull_power.shift(1)
    bull_decreasing = bull_power < bull_power.shift(1)
    bear_decreasing = bear_power < bear_power.shift(1)

    entry = (bear_power < 0) & bear_increasing & bull_increasing & ema_rising
    entry = entry.fillna(False)

    exit_signal = (~bear_increasing) | ((bull_power > 0) & bull_decreasing & bear_decreasing) | (~ema_rising)
    exit_signal = exit_signal.fillna(True)

    n = len(df)
    entry_arr = entry.to_numpy()
    exit_arr = exit_signal.to_numpy()
    pos_arr = [0] * n

    in_pos = False
    hold_counter = 0
    for i in range(n):
        if in_pos:
            hold_counter += 1
            exit_now = bool(exit_arr[i]) or hold_counter >= max_hold_days
            if exit_now:
                in_pos = False
                hold_counter = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if bool(entry_arr[i]):
                in_pos = True
                hold_counter = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    ema_period: int = 21,
    ema_slope_lookback: int = 5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        ema_period=ema_period,
        ema_slope_lookback=ema_slope_lookback,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
