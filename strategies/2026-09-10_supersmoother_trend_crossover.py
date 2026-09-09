"""Strategy: Ehlers 2-Pole SuperSmoother filter as a trend-crossover baseline.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-021):
John Ehlers' 2-pole SuperSmoother filter (Cybernetic Analysis for Stocks and
Futures, 2004, Equation 3-3) is a recursive Butterworth-style low-pass filter
that removes high-frequency noise with much less lag than a comparable SMA
or EMA. Per https://stonehillforex.com/2-pole-super-smoother-filter-as-a-baseline-indicator/,
it can be used directly as a trend "baseline": price crossing above the
SuperSmoother line (with the line itself sloping up) signals the start of an
uptrend; price crossing back below (or the line flattening/turning down)
signals the trend has ended. This is a plain trend-crossover application of
the filter, distinct from every other Ehlers strategy already tested in this
repo (Roofing Filter, Trendflex, Even Better Sinewave, Cyber Cycle, MESA
Stochastic, Instantaneous Trendline) which all use the SuperSmoother/highpass
combination as a denoising stage feeding into a cycle/oscillator construction
rather than as the crossover signal line itself.

SuperSmoother recursion (exact, per Ehlers Eq. 3-3, corroborated by
https://gist.github.com/flare9x/089be64732079134faa0a50332e4437b):
    a1 = exp(-1.414 * pi / n)
    b1 = 2 * a1 * cos(1.414 * 180 / n)   (degrees)
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3
    Super[i] = c1 * (x[i] + x[i-1]) / 2 + c2 * Super[i-1] + c3 * Super[i-2]

Signal logic
------------
- Apply the SuperSmoother (period `n`) to the close series.
- Long entry: close crosses above the SuperSmoother line AND the
  SuperSmoother's own `slope_lookback`-bar slope is positive (trend
  confirmation, avoids buying into a still-falling baseline).
- Exit: close crosses back below the SuperSmoother line, OR the
  SuperSmoother's slope turns negative, OR a max holding period of
  `max_hold_days` is reached.
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py): both generate_signals and
generate_returns accept the strategy's tunable parameters as keyword args.
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _super_smoother(close: pd.Series, n: int) -> pd.Series:
    """Ehlers 2-pole SuperSmoother filter (Eq. 3-3)."""
    a1 = math.exp(-1.414 * math.pi / n)
    b1 = 2 * a1 * math.cos(math.radians(1.414 * 180 / n))
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3

    vals = close.values
    out = [0.0] * len(vals)
    for i in range(len(vals)):
        if i < 2:
            out[i] = vals[i]
        else:
            out[i] = c1 * (vals[i] + vals[i - 1]) / 2.0 + c2 * out[i - 1] + c3 * out[i - 2]
    return pd.Series(out, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    n: int = 20,
    slope_lookback: int = 3,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    smoother = _super_smoother(close, n)
    slope = smoother.diff(slope_lookback)

    cross_up = (close > smoother) & (close.shift(1) <= smoother.shift(1))
    cross_down = (close < smoother) & (close.shift(1) >= smoother.shift(1))
    slope_up = slope > 0
    slope_down = slope < 0

    entry = cross_up & slope_up.fillna(False)
    exit_cross = cross_down.fillna(False)
    exit_slope = slope_down.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or bool(exit_slope.iloc[i]) or held >= max_hold_days:
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
