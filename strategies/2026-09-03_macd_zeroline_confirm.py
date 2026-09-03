"""Strategy: MACD(12,26,9) bullish signal-line cross, gated by a zero-line
confirmation filter, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-03-013):
Source: https://agentictraders.io/learn/macd-crossover-strategy — explains
the classic Gerald Appel MACD(12,26,9) construction (MACD line =
EMA(close,12)-EMA(close,26), signal line = EMA(MACD,9), histogram =
MACD-signal) and documents that raw signal-line crosses fire frequently
(8-15/month on a 4h BTC chart) and are prone to whipsaw in ranging markets,
while zero-line crosses (MACD line crossing above/below zero, i.e. the fast
EMA crossing the slow EMA) are rarer but "carry meaningfully higher win
rates in backtests" at the cost of later entry. The article's own proposed
fix is a "zero-line confirmation" filter: only take a bullish signal-line
cross when MACD is already above zero (or allow the cross itself to also be
the zero-line cross) rather than trading every signal-line cross
unconditionally.

This is the first MACD/EMA-convergence-family strategy tested in this repo
-- distinct from every prior entry (SMA crossover, Bollinger mean-reversion,
absolute momentum with/without vol-targeting or 200d trend filter, RSI(2)
mean-reversion, turn-of-month calendar, overnight drift, Donchian breakout,
time-series short-term reversal, gap-down fade, Bollinger squeeze breakout,
12m TSMOM monthly rebalance).

Signal logic
------------
- Compute standard MACD(fast=12, slow=26, signal=9) via EMAs.
- Entry (long): MACD line crosses above the signal line (bullish signal-line
  cross) AND (if `require_zero_confirm=True`) MACD line is currently >= 0
  at the time of the cross (zero-line confirmation filter from the source).
- Exit: MACD line crosses below the signal line (bearish signal-line cross).
- Flat otherwise; long-only (no shorts), per SAFETY.md.

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


def _macd_lines(close: pd.Series, fast: int, slow: int, signal: int):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line


def generate_signals(
    price_df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    require_zero_confirm: bool = True,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    macd_line, signal_line = _macd_lines(close, fast, slow, signal)

    above = macd_line > signal_line
    prev_above = above.shift(1).fillna(False)

    bull_cross = above & (~prev_above)
    bear_cross = (~above) & prev_above

    if require_zero_confirm:
        bull_cross = bull_cross & (macd_line >= 0)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(bear_cross.iloc[i]):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(bull_cross.iloc[i]):
                in_position = True
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    # Shift position by 1 day: yesterday's signal determines today's return
    # exposure (avoid look-ahead bias).
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
