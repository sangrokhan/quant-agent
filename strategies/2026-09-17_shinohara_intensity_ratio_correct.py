"""Strategy: Shinohara Intensity Ratio (SIR) -- correct ratio-of-sums formula.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-056):
Per ChartIQ's official Studies Reference Guide (Strong Ratio: "a moving
sum of a bar's High less the prior bar's Close divided by the prior
Close less the Low"; Weak Ratio: "a moving sum of the High-Close divided
by Close-Low"), the correct Shinohara Intensity Ratio construction is a
RATIO OF ROLLING SUMS of directional range components relative to the
PRIOR close (Strong Ratio) or CURRENT close (Weak Ratio) -- not the
per-bar intrabar-close-position average that this repo's prior Shinohara
attempt (2026-09-08-051, rejected decisively) implemented. That prior
entry used SMA((Close-Low)/(High-Low)) for "Strong Ratio" and
SMA((High-Close)/(High-Low)) for "Weak Ratio" -- an intrabar-close-
location construction resembling %K/Williams %R, NOT the true Shinohara
formula, which explicitly separates "prior close" (Strong Ratio
numerator/denominator) from "current close" (Weak Ratio) to capture true
directional GAP-plus-RANGE intensity, summed (not averaged) over the
window so strong trending runs compound rather than mean-revert to a
bounded [0,1] oscillator.

Formula (period = sir_window):
    StrongRatio_t = sum_{i=t-w+1}^{t} max(High_i - Close_{i-1}, 0)
                    / sum_{i=t-w+1}^{t} max(Close_{i-1} - Low_i, eps)
    WeakRatio_t   = sum_{i=t-w+1}^{t} max(High_i - Close_i, 0)
                    / sum_{i=t-w+1}^{t} max(Close_i - Low_i, eps)

Signal logic
------------
Long entry when StrongRatio crosses above WeakRatio (buying intensity,
measured against the PRIOR close, now exceeds selling intensity measured
against the CURRENT close -- true upside momentum building); exit on the
reverse cross, backstopped by a max_hold_days time-stop. Distinct
indicator construction from 2026-09-08-051 despite the same name -- a
correction of that prior entry's formula error, not a re-parameterization.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _compute_sir(high: pd.Series, low: pd.Series, close: pd.Series, window: int):
    prior_close = close.shift(1)

    strong_num = (high - prior_close).clip(lower=0.0)
    strong_den = (prior_close - low).clip(lower=1e-9)
    weak_num = (high - close).clip(lower=0.0)
    weak_den = (close - low).clip(lower=1e-9)

    strong_ratio = strong_num.rolling(window).sum() / strong_den.rolling(window).sum()
    weak_ratio = weak_num.rolling(window).sum() / weak_den.rolling(window).sum()
    return strong_ratio, weak_ratio


def generate_signals(
    price_df: pd.DataFrame,
    sir_window: int = 26,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series from SIR Strong/Weak cross."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    strong_ratio, weak_ratio = _compute_sir(high, low, close, sir_window)

    bullish = strong_ratio > weak_ratio
    bullish = bullish.fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    prev_bullish = False
    for i in range(len(df)):
        b = bool(bullish.iloc[i])
        if not in_pos:
            if b and not prev_bullish:
                in_pos = True
                hold_count = 0
        else:
            hold_count += 1
            if (not b) or hold_count >= max_hold_days:
                in_pos = False
                hold_count = 0
        position.iloc[i] = int(in_pos)
        prev_bullish = b
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
