"""Strategy: Ascending Scallop continuation breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id 2026-09-21-224):
Per LuxAlgo's "Scallop" concept page (https://www.luxalgo.com/library/concept/scallop,
read via browser_exec this iteration), a Scallop (Thomas Bulkowski, Encyclopedia
of Chart Patterns) is a curved mid-trend CONTINUATION pattern shaped like the
letter J: within an established uptrend, price rounds off in a gradual decline,
bottoms out smoothly (no sharp V-shaped vertex), then curls back UP through the
curve's own starting high -- confirming trend continuation. Source's own
disclosed trading rule: "traders buy an ascending scallop as price curls up
through the curve's starting high, with a stop under the rounded low, treating
the completed J as trend confirmation."

Key distinguishing feature vs other rounded-reversal patterns already tested in
this repo: the Scallop is explicitly a smaller, repeating MID-TREND feature
(source: "essentially a mid-trend rounding turn, smaller and repeating, rather
than a major reversal base"), unlike Rounding Bottom (large standalone reversal
base) or Cup-and-Handle (adds a second smaller pullback/handle after the main
curve, already tested 2026-09-06-172). This is the first Scallop-family
strategy in this repo (0 prior "scallop" hits in strategies_index.jsonl).

Operationalized signal logic (long-only)
------------------------------------------
Since the pattern's curve boundary is inherently subjective (source's own
caveat: "curves are identified by eye... that softness should temper
confidence in any precise scallop-based rule"), we approximate the "smooth
rounded decline-then-rise" shape numerically over a rolling window:

- Trend context: close[t-curve_window] < close[t] * uptrend_tolerance is NOT
  required directly; instead we require the window's END point (close[t]) to
  exceed the window's START point (close[t-curve_window]) -- this IS the
  "finish" criterion (source: "the right side should carry price above the
  curve's starting point").
- Curve shape check: split the window into two halves. The first half's
  close-vs-time correlation must be negative (declining leg of the J) and
  below -min_corr; the second half's correlation must be positive (rising
  leg) and above +min_corr. This operationalizes "smooth curve, not V-shaped"
  by requiring BOTH legs to show consistent (not choppy/spiky) directional
  drift, rather than allowing a single sharp reversal bar to qualify.
- Breakout confirmation: close[t] > close[t-curve_window] (curve's starting
  high) -- the entry trigger itself, evaluated fresh each bar (a new
  breakout above a completed curve's start).
- Trend precondition: close[t] > SMA(trend_window) (must occur within a
  broader uptrend, per source's explicit ascending-scallop context
  requirement).
- Exit: close falls below the curve's own rounded low (the window minimum,
  source's own disclosed stop-loss reference) OR max_hold_days reached.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  {0,1} position series
    generate_returns(price_df, **params) -> pd.Series  daily strategy returns
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


def _rolling_corr_with_time(series: pd.Series, window: int) -> pd.Series:
    """Rolling Pearson correlation of `series` values against a simple
    0..window-1 time index, ending at each bar."""
    x = np.arange(window)
    x_mean = x.mean()
    x_centered = x - x_mean
    x_ss = (x_centered ** 2).sum()

    def _corr(y: np.ndarray) -> float:
        if np.isnan(y).any():
            return np.nan
        y_centered = y - y.mean()
        y_ss = (y_centered ** 2).sum()
        if x_ss == 0 or y_ss == 0:
            return 0.0
        return float((x_centered * y_centered).sum() / np.sqrt(x_ss * y_ss))

    return series.rolling(window).apply(lambda y: _corr(np.asarray(y)), raw=False)


def generate_signals(
    price_df: pd.DataFrame,
    curve_window: int = 30,
    min_corr: float = 0.3,
    trend_window: int = 100,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    half = curve_window // 2

    # Correlation of first-half window (declining leg) vs time.
    # Build via shifting: correlation computed on close.shift(half) over `half`
    # bars ending `half` bars ago (the first half of the full curve_window).
    corr_first_half = _rolling_corr_with_time(close, half).shift(half)
    corr_second_half = _rolling_corr_with_time(close, half)

    curve_start = close.shift(curve_window)
    curve_low = close.rolling(curve_window).min()

    finish_above_start = close > curve_start
    shape_ok = (corr_first_half <= -min_corr) & (corr_second_half >= min_corr)

    sma = close.rolling(trend_window).mean()
    trend_ok = close > sma

    entry = (
        finish_above_start.fillna(False)
        & shape_ok.fillna(False)
        & trend_ok.fillna(False)
    )

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_low = np.nan

    closes = close.values
    curve_low_vals = curve_low.values
    entry_vals = entry.values

    for i in range(n):
        if in_position:
            held = i - entry_idx
            stop_hit = (not np.isnan(stop_low)) and closes[i] < stop_low
            if stop_hit or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_vals[i]):
                in_position = True
                entry_idx = i
                stop_low = curve_low_vals[i]
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
