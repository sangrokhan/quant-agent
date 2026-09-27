"""Strategy: Ultimate Oscillator (Williams) oversold-reversal, long-only.

Hypothesis (source: https://gainium.io/help/ultimate-oscillator, "Strategy 1:
Overbought/Oversold Reversal Strategy", read 2026-09-27):
The Ultimate Oscillator (UO) combines momentum measured over three
timeframes (fast=7, mid=14, slow=28 periods by default) into a single
weighted 0-100 oscillator, designed to reduce false reversal signals vs a
single-period oscillator like plain RSI or Stochastic. Source's disclosed
rule: enter long when UO crosses below the oversold level (30), exit when
UO crosses back above the midline (50) as upward momentum fades. This repo
adapts the long-only half of that rule (per SAFETY.md, no short side).

First Ultimate Oscillator strategy in this repo (0 prior hits in
strategies_index.jsonl for "Ultimate Oscillator" / "UO"), distinct from all
prior single-timeframe RSI/Stochastic/CCI/CMO oscillator-threshold
strategies already tried (e.g. RSI2 mean-rev, Stochastic RSI, CCI oversold)
because UO's own construction already blends 3 lookback periods rather than
using one raw oscillator value.

Ultimate Oscillator formula (Larry Williams, 1976):
    BP  (buying pressure)  = close - min(low, prior_close)
    TR  (true range)       = max(high, prior_close) - min(low, prior_close)
    Avg1 = sum(BP, fast)  / sum(TR, fast)
    Avg2 = sum(BP, mid)   / sum(TR, mid)
    Avg3 = sum(BP, slow)  / sum(TR, slow)
    UO = 100 * (4*Avg1 + 2*Avg2 + 1*Avg3) / 7

Signal logic
------------
- Entry (long): UO crosses from >= oversold_level up through < oversold_level
  is the trigger point per source ("crosses below 30" is treated here as the
  bar UO first dips under the oversold threshold, entering on the next bar's
  open equivalent via the standard next-day-return-shift used across this
  repo).
- Exit: UO crosses back above exit_level (50, source's own midline exit) OR
  a max_hold_days time-stop (consistent with other mean-reversion strategies
  in this repo, to avoid indefinite holds through prolonged low-UO chop).
- Flat otherwise.

Interface contract (see validation/validators.py and validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _ultimate_oscillator(
    df: pd.DataFrame, fast: int = 7, mid: int = 14, slow: int = 28
) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prior_close = close.shift(1)

    bp = close - pd.concat([low, prior_close], axis=1).min(axis=1)
    tr = pd.concat([high, prior_close], axis=1).max(axis=1) - pd.concat(
        [low, prior_close], axis=1
    ).min(axis=1)

    bp_sum_fast = bp.rolling(fast).sum()
    tr_sum_fast = tr.rolling(fast).sum()
    bp_sum_mid = bp.rolling(mid).sum()
    tr_sum_mid = tr.rolling(mid).sum()
    bp_sum_slow = bp.rolling(slow).sum()
    tr_sum_slow = tr.rolling(slow).sum()

    avg1 = bp_sum_fast / tr_sum_fast.replace(0, pd.NA)
    avg2 = bp_sum_mid / tr_sum_mid.replace(0, pd.NA)
    avg3 = bp_sum_slow / tr_sum_slow.replace(0, pd.NA)

    uo = 100 * (4 * avg1 + 2 * avg2 + 1 * avg3) / 7
    return uo


def generate_signals(
    price_df: pd.DataFrame,
    fast: int = 7,
    mid: int = 14,
    slow: int = 28,
    oversold_level: float = 30.0,
    exit_level: float = 50.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    uo = _ultimate_oscillator(df, fast=fast, mid=mid, slow=slow)

    below_oversold = uo < oversold_level
    entry = below_oversold & (~below_oversold.shift(1).fillna(False))
    exit_midline = uo > exit_level

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(df)):
        if in_position:
            held = i - entry_idx
            if bool(exit_midline.iloc[i]) or held >= max_hold_days:
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
