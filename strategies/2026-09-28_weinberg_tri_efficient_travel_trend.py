"""Strategy: Weinberg's TRI ("The Range Indicator") efficient-travel trend entry.

Hypothesis (source: https://www.luxalgo.com/library/indicator/the-range-indicator/,
read 2026-09-28 via browser_exec after browsing LuxAlgo's indicator library
listing page for a fresh, not-yet-tested indicator -- Vortex/Ehlers Cyber
Cycle/Volume Zone Oscillator/NR7/Cup-and-Handle/Head-and-Shoulders/
SuperTrend/Camarilla(-mean-reversion)/Elder SafeZone/AMD POC/Value Area
Reversion/No-Wick Retest/Higher-TF Stochastic Buckets all already saturated
in this repo per strategies_index.jsonl novelty checks this iteration):

Jack Weinberg's TRI (The Range Indicator) measures whether a bar is
"covering ground or just covering range": each bar's true range is set
against its close-to-close progress (the ratio at the indicator's heart),
then normalized stochastic-style over a `normalization_length`-bar lookback
and smoothed into a 0-100 line with an EMA of length `smoothing_length`.
Per the source's own disclosed formula summary ("each bar's true range over
its close-to-close gain on up-closing bars"):
    raw_ratio[t] = true_range[t] / max(|close[t] - close[t-1]|, epsilon)
(true range = max(high-low, |high-prior_close|, |low-prior_close|)).
High readings (churn) mean in-bar noise is swamping the ground gained --
Weinberg read this as a trend-EXHAUSTION warning. Low readings mean
efficient travel -- the source explicitly states this is "the environment
Weinberg's study associated with trending conditions."

Source's own disclosed trading rule: "Cross below the Low Threshold:
efficient travel, progress large relative to in-bar noise, the environment
Weinberg's study associated with trending conditions." We operationalize
this as a trend-following LONG entry: TRI crossing below the low threshold
(default 20) while price is above a longer-term SMA trend filter (repo
convention, since TRI itself carries no directional information -- it only
measures HOW efficiently price is moving, not which way) signals a
genuinely efficient uptrend worth riding; exit when TRI crosses back above
the high threshold (churn returning, "trend-ending warning" per source) or
the trend filter breaks, or a max_hold_days time-stop backstop.

First Weinberg TRI / "Range Indicator" strategy in this repo (0 prior hits
for "Weinberg", "Range Indicator", "TRI" [as this specific indicator] in
strategies_index.jsonl) -- distinct from every other family already tested
(Choppiness Index measures a similar "trending vs. ranging" concept via a
different ATR-sum/range-ratio construction, and this repo's LuxAlgo FAQ
snippet itself flags "How is TRI different from the Choppiness Index?" as
a commonly-asked distinguishing question).

Signal logic
------------
- true_range = standard Wilder true range.
- raw_ratio = true_range / max(|close - close.shift(1)|, 1e-9).
- TRI_raw = 100 * (raw_ratio - rolling_min(raw_ratio, normalization_length))
            / (rolling_max(raw_ratio, normalization_length)
               - rolling_min(raw_ratio, normalization_length))
  (degenerate windows where max==min are output as 0, per the source's
  own "Output Zero" default convention).
- TRI = EMA(TRI_raw, smoothing_length).
- Entry (long): TRI crosses from >= low_threshold down through
  < low_threshold (fresh efficient-travel signal) AND close > SMA(trend_window).
- Exit: TRI crosses back above high_threshold, OR close falls below
  SMA(trend_window) (trend filter breaks), OR max_hold_days time-stop.

Interface contract (see validation/validators.py and validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _true_range(df: pd.DataFrame) -> pd.Series:
    prior_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prior_close).abs(),
            (df["low"] - prior_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _weinberg_tri(
    df: pd.DataFrame, normalization_length: int, smoothing_length: int
) -> pd.Series:
    tr = _true_range(df)
    close_progress = (df["close"] - df["close"].shift(1)).abs().clip(lower=1e-9)
    raw_ratio = tr / close_progress

    roll_min = raw_ratio.rolling(normalization_length).min()
    roll_max = raw_ratio.rolling(normalization_length).max()
    denom = (roll_max - roll_min).replace(0, np.nan)
    tri_raw = 100 * (raw_ratio - roll_min) / denom
    tri_raw = tri_raw.fillna(0.0)  # degenerate window -> Output Zero (source default)

    tri = tri_raw.ewm(span=smoothing_length, adjust=False).mean()
    return tri


def generate_signals(
    price_df: pd.DataFrame,
    normalization_length: int = 10,
    smoothing_length: int = 3,
    low_threshold: float = 20.0,
    high_threshold: float = 80.0,
    trend_window: int = 50,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    tri = _weinberg_tri(df, normalization_length, smoothing_length)
    sma = close.rolling(trend_window).mean()

    below_low = tri < low_threshold
    fresh_efficient = below_low & (~below_low.shift(1).fillna(False))
    above_high = tri > high_threshold
    trend_ok = close > sma

    entry = fresh_efficient & trend_ok

    pos = pd.Series(0.0, index=df.index)
    in_pos = False
    hold_count = 0
    for i in range(len(df)):
        if in_pos:
            hold_count += 1
            exit_now = (
                bool(above_high.iloc[i])
                or not bool(trend_ok.iloc[i])
                or hold_count >= max_hold_days
            )
            if exit_now:
                in_pos = False
                hold_count = 0
            else:
                pos.iloc[i] = 1.0
        if not in_pos and bool(entry.iloc[i]):
            in_pos = True
            hold_count = 0
            pos.iloc[i] = 1.0

    return pos


def generate_returns(
    price_df: pd.DataFrame,
    normalization_length: int = 10,
    smoothing_length: int = 3,
    low_threshold: float = 20.0,
    high_threshold: float = 80.0,
    trend_window: int = 50,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return the daily strategy return series (no transaction costs)."""
    df = _prep(price_df)
    pos = generate_signals(
        df,
        normalization_length=normalization_length,
        smoothing_length=smoothing_length,
        low_threshold=low_threshold,
        high_threshold=high_threshold,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0.0)
    return strat_ret
