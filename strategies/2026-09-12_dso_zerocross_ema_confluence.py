"""Strategy: Ehlers-style Deviation-Scaled Oscillator (DSO) zero-line cross
with EMA trend confluence.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
John Ehlers' deviation-scaling technique normalizes an oscillator's raw
deviation-from-smoothed-price by its own recent root-mean-square (RMS)
dispersion, producing a bounded, volatility-adaptive momentum measure that
(per source) "filters out noise better than a standard MACD or RSI" and
"adapts to changing volatility without needing constant manual adjustment".
Per https://theindicatorlab.com/reviews/ehlers-deviation-scaled-oscillator/
(via browser_exec -- google.com SERP; page read directly, not web_extract'd),
the disclosed entry/exit rule is: "Enter long when Oscillator crosses above
zero (momentum shift), Histogram turns green and is rising, Price is above a
key moving average (e.g. 50 EMA) for confluence." We operationalize this as:
DSO crossing above 0 while close > EMA(trend_window) triggers a long entry;
exit on DSO crossing back below 0, EMA trend break (close < EMA), or a
max_hold_days time-stop.

This is distinct from the already-tested Ehlers Deviation-Scaled MOVING
AVERAGE (DSMA, 2026-09-10-106/2026-09-11 adaptive follow-up) -- DSMA is an
adaptive-alpha trend-following MA, whereas this is a bounded MOMENTUM
OSCILLATOR with a zero-line cross rule, a different indicator/technique
family despite the shared "deviation scaled" name. First DSO-oscillator
strategy in this repo.

DSO construction (practical implementation of Ehlers' deviation-scaling
idea, since the exact proprietary Pine formula wasn't disclosed by the
source): 
  1. filt = EMA(close, dso_window)              # smoothed baseline
  2. deviation = close - filt
  3. rms = sqrt(rolling_mean(deviation**2, dso_window))
  4. dso = deviation / rms                       # ~z-score-like, bounded
  5. dso_smooth = EMA(dso, dso_smooth)            # histogram-style smoothing

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


def _compute_dso(close: pd.Series, dso_window: int, dso_smooth: int) -> pd.Series:
    filt = close.ewm(span=dso_window, adjust=False).mean()
    deviation = close - filt
    rms = (deviation.pow(2).rolling(dso_window).mean()).pow(0.5)
    dso_raw = deviation / rms.replace(0.0, pd.NA)
    dso = dso_raw.ewm(span=dso_smooth, adjust=False).mean()
    return dso


def generate_signals(
    price_df: pd.DataFrame,
    dso_window: int = 20,
    dso_smooth: int = 3,
    trend_window: int = 50,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    dso = _compute_dso(close, dso_window, dso_smooth)
    ema_trend = close.ewm(span=trend_window, adjust=False).mean()

    prev_dso = dso.shift(1)
    cross_up = (dso > 0) & (prev_dso <= 0)
    cross_down = (dso < 0) & (prev_dso >= 0)
    trend_up = close > ema_trend

    entry = cross_up.fillna(False) & trend_up.fillna(False)
    exit_cross = cross_down.fillna(False)
    exit_trend_break = ~trend_up.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
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
