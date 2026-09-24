"""Strategy: Bill Williams Accelerator Oscillator (AC) two-consecutive-bar
color-streak signal, daily bars.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-XXX):
Per https://admiralmarkets.com/education/articles/forex-indicators/accelerator-oscillator
(browser_exec, web_extract failed -- ddgs backend search-only): "a possible
Accelerator Oscillator strategy could interpret two green columns in a row
above zero as a buy signal, and two red columns in a row below the zero
line as a sell signal." This is a DISTINCT entry rule from the repo's prior
AC strategies (2026-09-06-173/174, 2026-09-14-174), which all use a plain
zero-line crossover or continuous z-scored sizing dial on the raw AC value
-- this one requires TWO consecutive same-direction bars (AC[t] > AC[t-1]
AND AC[t-1] > AC[t-2], i.e. "green"/rising) while AC stays above zero
(momentum accelerating, not just crossing), a materially different (and
per the source, stricter/more-confirmed) trigger condition.

Signal logic
------------
- AO (Awesome Oscillator) = SMA(5, median_price) - SMA(34, median_price),
  median_price = (high+low)/2.
- AC (Accelerator Oscillator) = AO - SMA(5, AO).
- A bar is "green" (rising) if AC[t] > AC[t-1]; "red" (falling) otherwise.
- Entry (long): AC[t] > 0 AND AC[t] > AC[t-1] AND AC[t-1] > AC[t-2] (two
  consecutive green/rising bars while above zero).
- Exit: two consecutive red/falling bars (AC[t] < AC[t-1] AND
  AC[t-1] < AC[t-2]), OR AC crosses back below zero, OR after
  max_hold_days.
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


def _accelerator_oscillator(df: pd.DataFrame, ao_fast: int = 5, ao_slow: int = 34, ac_smooth: int = 5) -> pd.Series:
    median_price = (df["high"] + df["low"]) / 2.0
    ao = median_price.rolling(ao_fast).mean() - median_price.rolling(ao_slow).mean()
    ac = ao - ao.rolling(ac_smooth).mean()
    return ac


def generate_signals(
    price_df: pd.DataFrame,
    ao_fast: int = 5,
    ao_slow: int = 34,
    ac_smooth: int = 5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ac = _accelerator_oscillator(df, ao_fast=ao_fast, ao_slow=ao_slow, ac_smooth=ac_smooth)
    rising = ac > ac.shift(1)
    falling = ac < ac.shift(1)

    two_green_above_zero = (ac > 0) & rising & rising.shift(1).fillna(False)
    two_red = falling & falling.shift(1).fillna(False)
    zero_cross_down = (ac < 0) & (ac.shift(1) >= 0)

    entry = two_green_above_zero.to_numpy()
    exit_pattern = (two_red | zero_cross_down).to_numpy()

    position = pd.Series(0, index=close.index, dtype=int)
    pos_arr = position.to_numpy().copy()

    in_position = False
    hold_days = 0
    for i in range(len(close)):
        if in_position:
            hold_days += 1
            if exit_pattern[i] or hold_days >= max_hold_days:
                in_position = False
                hold_days = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if entry[i]:
                in_position = True
                hold_days = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    position = pd.Series(pos_arr, index=close.index, dtype=int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    ao_fast: int = 5,
    ao_slow: int = 34,
    ac_smooth: int = 5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df, ao_fast=ao_fast, ao_slow=ao_slow, ac_smooth=ac_smooth, max_hold_days=max_hold_days
    )
    daily_ret = close.pct_change()
    strat_ret = position.shift(1).fillna(0) * daily_ret
    strat_ret = strat_ret.fillna(0.0)
    return strat_ret
