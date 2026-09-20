"""Strategy: Fractional-ATR-Distance Breakout with ATR Stop-Loss (rescue).

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD):
Direct rescue attempt of prior near-miss 2026-09-20-137 (Fractional-ATR-
Distance Breakout, Fixed-Bar Exit, per Ali Casey's StatOasis article
"Same Breakout Strategy, Different Results: Nasdaq vs. SP500 vs. Dow",
https://statoasis.com/overfit/research/same-breakout-strategy-different-results-nasdaq-vs-sp500-vs-dow).
That strategy passed Sharpe/transaction-cost-survival/walk-forward/
parameter-sensitivity excellently on equity (QQQ Sharpe 1.093, SPY 1.045,
relative_std 0.16-0.18 -- among the most parameter-robust strategies
tested in this repo) but decisively FAILED max-drawdown on all symbols
(QQQ 0.356, SPY 0.285, BTC/USDT 0.784) because the source's own design
deliberately omits any stop-loss ("no complicated oscillators... no stop
loss"). This repo's own knowledge base explicitly flagged the "obvious
next-iteration follow-up: add a hard ATR-multiple stop-loss (this repo's
standard fix, e.g. Turtle System 1's 2N stop) to the SAME entry/hold-period
mechanic to see if tail-risk containment rescues the drawdown without
materially hurting the strong Sharpe/robustness profile."

This iteration implements exactly that fix: identical entry trigger and
fixed-bar exit mechanic, but adds an ATR-multiple stop-loss (checked
intrabar via the day's low) that can exit BEFORE the fixed hold_days
elapses if triggered. No new external research needed -- this is a
same-cron-trigger direct parameter/mechanism rescue of an already-sourced
hypothesis, per RESEARCH_LOOP.md Step 3's allowance for "meaningfully
varying" a near-miss by "specifically addressing the prior rejection
reason."

Signal logic
------------
- entry_level = prior day's close + atr_frac * ATR(atr_window) (unchanged
  from 2026-09-20-137).
- Entry (long): today's high clears entry_level.
- Stop-loss: stop_level = entry_price - stop_atr_mult * ATR(atr_window) at
  entry (Turtle-System-1-style N-multiple stop, fixed at entry, not
  trailing). If a day's low breaches stop_level, exit that day at the stop
  level (approximated here via that day's close for simplicity, consistent
  with this repo's other close-based execution strategies).
- Exit (unchanged mechanic): whichever comes first of (a) the ATR stop-loss
  triggering, or (b) exactly hold_days bars after entry (source's original
  fixed-bar exit, now a secondary/backstop exit rather than the only one).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    atr_window: int = 10,
    atr_frac: float = 0.25,
    hold_days: int = 5,
    stop_atr_mult: float = 2.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    atr = _atr(df, atr_window)
    entry_level = close.shift(1) + atr_frac * atr.shift(1)
    entry_trigger = (high >= entry_level).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_price = 0.0
    stop_level = 0.0

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if low.iloc[i] <= stop_level:
                in_position = False
                position.iloc[i] = 0
                continue
            if held >= hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
                in_position = True
                entry_idx = i
                entry_price = entry_level.iloc[i]
                atr_at_entry = atr.shift(1).iloc[i]
                if pd.isna(atr_at_entry):
                    atr_at_entry = 0.0
                stop_level = entry_price - stop_atr_mult * atr_at_entry
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
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
