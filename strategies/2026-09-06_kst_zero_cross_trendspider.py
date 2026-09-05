"""Strategy: KST (Know Sure Thing) zero-line crossover, using TrendSpider's
alternate (9,12,18,24)-period weighting instead of Pring's classic
(10,15,20,30) periods, and a ZERO-LINE cross entry instead of a signal-line
cross entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-100):
Per TrendSpider's KST Learning Center article, "buy signals are generated
when the KST crosses the zero line", and the article's own formula example
uses smoothed-ROC periods 9, 12, 18, 24 weighted x1/x2/x3/x4 -- a distinct
period set from Martin Pring's original 10/15/20/30 used by this repo's
prior KST entry (2026-09-04-057, rejected: near-miss on QQQ, used
signal-line crossover while at/below zero, not a pure zero-line cross).
This iteration tests the pure zero-line-cross trigger with TrendSpider's
period set to see whether the simpler zero-cross rule (vs. requiring a
signal-line cross while below zero) performs differently.

Signal logic
------------
- KST = sum of 4 SMA-smoothed ROC values at periods (roc1,roc2,roc3,roc4),
  each smoothed by an SMA of the same window as its ROC period (standard
  simplification), weighted by (1,2,3,4).
- Entry (long): KST crosses above zero (KST[t]>0 and KST[t-1]<=0).
- Exit: KST crosses back below zero, OR a max_hold_days time-stop.
- Flat otherwise.

Interface contract: both generate_signals and generate_returns accept all
tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _smoothed_roc(close: pd.Series, roc_period: int, smooth_window: int) -> pd.Series:
    roc = close.pct_change(roc_period) * 100
    return roc.rolling(smooth_window).mean()


def _kst(
    close: pd.Series,
    roc1: int,
    roc2: int,
    roc3: int,
    roc4: int,
    smooth1: int,
    smooth2: int,
    smooth3: int,
    smooth4: int,
) -> pd.Series:
    r1 = _smoothed_roc(close, roc1, smooth1) * 1
    r2 = _smoothed_roc(close, roc2, smooth2) * 2
    r3 = _smoothed_roc(close, roc3, smooth3) * 3
    r4 = _smoothed_roc(close, roc4, smooth4) * 4
    return r1 + r2 + r3 + r4


def generate_signals(
    price_df: pd.DataFrame,
    roc1: int = 9,
    roc2: int = 12,
    roc3: int = 18,
    roc4: int = 24,
    smooth_window: int = 9,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    ``smooth_window`` applies uniformly to smoothing all 4 ROC legs (a
    simplification of TrendSpider's article, which doesn't specify distinct
    per-leg smoothing windows) -- the single tunable smoothing knob the grid
    test sweeps.
    """
    df = _prep(price_df)
    close = df["close"]

    kst = _kst(
        close, roc1, roc2, roc3, roc4,
        smooth_window, smooth_window, smooth_window, smooth_window,
    )

    cross_up = (kst > 0) & (kst.shift(1) <= 0)
    cross_down = (kst < 0) & (kst.shift(1) >= 0)

    entry = cross_up.fillna(False)
    exit_signal = cross_down.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
