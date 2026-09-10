"""Strategy: RAVI (Range Action Verification Index, Tushar Chande) trend
confirmation with threshold entry and zero-reversion exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-XXX):
Per technicalresources.in's "How to Trade Using the Range Action
Verification Index (RAVI)" (visited this iteration,
https://technicalresources.in/how-to-trade-using-the-range-action-verification-index-ravi-strategies-and-examples/):
RAVI = 100 * (SMA_short - SMA_long) / SMA_long (source's default periods:
7-period short SMA, 65-period long SMA). RAVI measures the percentage
divergence between a short and long SMA, distinguishing trending
(|RAVI| large) from ranging (RAVI near 0) markets. Source's "Trend
Confirmation Strategy" (Strategy #1, fully disclosed mechanical rule):
enter long when RAVI rises above a threshold (default 3%, confirming an
uptrend), exit when RAVI starts declining back toward zero (weakening
trend). Long-only per SAFETY.md (source's own rule is symmetric
long/short).

This is a first RAVI strategy in this repo -- distinct from every other
SMA-crossover-family and moving-average-ratio strategy already tested
(e.g. plain SMA crossover, GAPO log-range index, MA-ribbon/GMMA) because
RAVI is specifically a *normalized percentage gap between two SMAs*, and
the entry/exit rule (threshold-crossing entry, "start declining toward
zero" exit -- i.e. RAVI's own downward slope, not a level crossing) is a
unique combination not implemented elsewhere in this repo.

Signal logic
------------
- ravi[t] = 100 * (SMA(close, short_window)[t] - SMA(close, long_window)[t]) / SMA(close, long_window)[t]
- Entry (long): ravi crosses above entry_threshold (e.g. 3.0).
- Exit: ravi has been declining over the trailing exit_slope_window bars
  (ravi.diff(exit_slope_window) < 0) while already in a position (source's
  "starts declining toward zero" rule, operationalized as a negative
  slope rather than waiting for an exact zero-cross, since RAVI can
  reverse well above zero and the source's own example describes acting
  on the peak-and-decline, not a level cross), OR a max_hold_days
  time-stop as a safety backstop.

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


def _ravi(close: pd.Series, short_window: int, long_window: int) -> pd.Series:
    sma_short = close.rolling(short_window).mean()
    sma_long = close.rolling(long_window).mean()
    return 100.0 * (sma_short - sma_long) / sma_long


def generate_signals(
    price_df: pd.DataFrame,
    short_window: int = 7,
    long_window: int = 65,
    entry_threshold: float = 3.0,
    exit_slope_window: int = 3,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ravi = _ravi(close, short_window, long_window)
    prev_ravi = ravi.shift(1)

    entry = (prev_ravi < entry_threshold) & (ravi >= entry_threshold)
    declining = ravi.diff(exit_slope_window) < 0
    exit_condition = declining.fillna(False)

    entry = entry.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_condition.iloc[i]) or held >= max_hold_days:
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
