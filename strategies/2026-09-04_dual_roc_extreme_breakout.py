"""Strategy: Dual-timeframe Rate of Change (ROC) momentum with extreme-point
breakout entry and ATR-stop / time exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-092):
Per oxfordstrat.com's published dual-momentum ROC system (40yr, 42 futures
markets): a SLOW ROC (lookback = roc1_window) acts as a trend FILTER (only
trade long when ROC1 > 0), a FASTER ROC (lookback = roc2_window, typically
half of roc1_window) acts as the SETUP (only trade long when ROC2 > 0), and
entry triggers when price breaks above the "extreme point" -- the highest
close reached while both filter and setup have been positive -- approximated
here as a breakout above the rolling max close over roc2_window while both
ROC filters are positive. Exit via a fixed time exit (time_index bars) OR an
ATR-based stop (atr_stop_mult * ATR(atr_window) below entry), whichever
comes first. Source's own published Sharpe for this construction on
40yr/42-futures data tops out around 0.90 -- testing here to see if the
equity/crypto daily-bar adaptation performs differently.

Signal logic
------------
- roc1[t] = (close[t] - close[t-roc1_window]) / close[t-roc1_window]  (slow filter)
- roc2[t] = (close[t] - close[t-roc2_window]) / close[t-roc2_window]  (fast setup)
- extreme_point[t] = rolling max close over roc2_window, computed only over
  bars where roc1>0 and roc2>0 (approximated via forward-fill of the max
  close while both conditions hold)
- Entry: roc1[t] > 0 AND roc2[t] > 0 AND close[t] > extreme_point[t-1]
- Exit: hold_days >= time_index, OR close[t] <= entry_price - atr_stop_mult
  * ATR(atr_window) at entry (fixed stop, not trailing)

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window, min_periods=1).mean()


def generate_signals(
    price_df: pd.DataFrame,
    roc1_window: int = 100,
    roc2_window: int = 50,
    time_index: int = 60,
    atr_window: int = 20,
    atr_stop_mult: float = 4.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    atr = _atr(df, atr_window)

    roc1 = close.pct_change(roc1_window)
    roc2 = close.pct_change(roc2_window)
    both_positive = (roc1 > 0) & (roc2 > 0)
    extreme_point = close.rolling(roc2_window, min_periods=1).max()

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    entry_stop = np.nan
    for i in range(n):
        if in_pos:
            hold_count += 1
            time_exit = hold_count >= time_index
            stop_exit = close.iloc[i] <= entry_stop
            if time_exit or stop_exit:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if i > 0 and bool(both_positive.iloc[i]) and close.iloc[i] > extreme_point.iloc[i - 1]:
                in_pos = True
                hold_count = 0
                entry_stop = close.iloc[i] - atr_stop_mult * atr.iloc[i]
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    roc1_window: int = 100,
    roc2_window: int = 50,
    time_index: int = 60,
    atr_window: int = 20,
    atr_stop_mult: float = 4.0,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        roc1_window=roc1_window,
        roc2_window=roc2_window,
        time_index=time_index,
        atr_window=atr_window,
        atr_stop_mult=atr_stop_mult,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
