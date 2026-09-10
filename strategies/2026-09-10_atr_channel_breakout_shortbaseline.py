"""Strategy: ATR Channel Breakout, short-baseline retune of near-miss 2026-09-09-096.

Hypothesis (see knowledge_base/strategies_log.jsonl for this run's id):
Direct follow-up to near-miss 2026-09-09-096 (ATR Channel Breakout,
baseline_window=350, atr_mult=[3,5,7]; QQQ/SPY both near-missed full-sample
Sharpe (0.68-0.73 vs 1.0 threshold) at very low trade frequency (~2-3
trades/year over 8.7yr) with the 350-day baseline. That entry's own `notes`
field explicitly suggested: "shorten baseline_window (e.g. 100) with a wider
ATR mult ... to increase trade frequency ... and possibly clear Sharpe."

This iteration re-uses the identical TradingBlox-style ATR-channel breakout
mechanics (source: TradingCode/TradingBlox/StockGro synthesis, already read
in 2026-09-09-096 -- a parameter-retune iteration re-uses the prior
iteration's source per RESEARCH_LOOP.md, same pattern as the QP QQQ retune
2026-09-10-068) but tests a materially shorter baseline_window=100 (vs 350)
paired with a correspondingly wider atr_mult sweep, to check whether more
frequent, shorter-baseline signals clear the Sharpe/MDD thresholds that the
slow 350-day variant narrowly missed.

Signal logic (identical construction, different window)
---------------------------------------------------------
- baseline = SMA(close, baseline_window) [this iteration: 100, vs prior 350]
- atr = ATR(high, low, close, atr_window) [20]
- upper_channel = baseline + atr_mult * atr
- Entry (long): close crosses from at/below upper_channel to above it.
- Exit: close crosses back below baseline, OR max_hold_days time-stop.

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


def _atr(df: pd.DataFrame, window: int = 20) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    baseline_window: int = 100,
    atr_window: int = 20,
    atr_mult: float = 4.0,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    baseline = close.rolling(baseline_window).mean()
    atr = _atr(df, atr_window)
    upper_channel = baseline + atr_mult * atr

    above_upper = close > upper_channel
    entry = above_upper & (~above_upper.shift(1).fillna(False))
    exit_baseline = close < baseline

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_baseline.iloc[i]) or held >= max_hold_days:
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
