"""Strategy: Coral Trend (Tim Tillson's T3 moving average) slope-flip signal.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-131):
The "Coral" indicator (originator uncredited, widely ported since ~2015) is
a color-coded plot of Tim Tillson's T3 moving average -- a sextuple
cascaded EMA recombined via a fixed polynomial of one volume-factor
constant b, giving a smoother, less-laggy line than a simple/exponential
MA of the same period. Per
[stonehillforex.com](https://stonehillforex.com/2022/09/coral-as-a-confirmation-indicator/):
"Long: The signal line goes from red, to yellow, to blue. The entry is the
open of the period after yellow... Short: The signal line goes from blue,
to yellow, to red." I.e. color encodes the T3 line's local slope direction
(red=falling, blue=rising, yellow=transition/near-flat), and the systematic
rule is to enter on the first bar after the slope flips from
falling to rising (long) and treat a flip back to falling as the exit.
Using the source's own default period (34) and Tillson's standard volume
factor (b=0.7). First T3/Coral-family strategy tested in this repo --
distinct from all prior MA-crossover strategies (SMA/EMA/HMA/ZLEMA/DEMA/
TEMA/KAMA/McGinley Dynamic) since T3's sextuple-EMA-of-EMA cascade with the
c1..c4 polynomial recombination is a fundamentally different (much smoother,
near-zero-overshoot) construction than any single/double/triple EMA already
tested, and the signal here is the line's OWN slope-flip rather than a
crossover against price or a second MA.

Signal logic
------------
- period: EMA period for each of the 6 cascaded smoothing stages
  (default 34, the source's default).
- b: Tillson's volume factor constant (default 0.7, standard).
- Long entry: T3 slope flips from <=0 to >0 (first bar of a new "blue"
  uptrend after a "yellow" transition).
- Exit: T3 slope flips from >0 to <=0 (flips back toward "red"), OR a
  max_hold_days time-stop.

Interface contract for validators (see validation/validators.py) and
grid_test.py: generate_signals/generate_returns take price_df plus keyword
params.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _t3(close: pd.Series, period: int, b: float) -> pd.Series:
    e1 = close.ewm(span=period, adjust=False).mean()
    e2 = e1.ewm(span=period, adjust=False).mean()
    e3 = e2.ewm(span=period, adjust=False).mean()
    e4 = e3.ewm(span=period, adjust=False).mean()
    e5 = e4.ewm(span=period, adjust=False).mean()
    e6 = e5.ewm(span=period, adjust=False).mean()

    c1 = -(b ** 3)
    c2 = 3 * b ** 2 + 3 * b ** 3
    c3 = -6 * b ** 2 - 3 * b - 3 * b ** 3
    c4 = 1 + 3 * b + b ** 3 + 3 * b ** 2

    t3 = c1 * e6 + c2 * e5 + c3 * e4 + c4 * e3
    return t3


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 34,
    b: float = 0.7,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    t3 = _t3(close, period, b)
    slope = t3.diff()

    flip_up = (slope > 0) & (slope.shift(1) <= 0)
    flip_down = (slope < 0) & (slope.shift(1) >= 0)

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_now = bool(flip_down.iloc[i]) if pd.notna(flip_down.iloc[i]) else False
            if exit_now or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            entry_now = bool(flip_up.iloc[i]) if pd.notna(flip_up.iloc[i]) else False
            if entry_now:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    period: int = 34,
    b: float = 0.7,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(df, period=period, b=b, max_hold_days=max_hold_days)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
