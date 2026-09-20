"""Strategy: Price MACD Crossover Gated by OBV-MACD Confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-135):
Per Ali Casey's StatOasis study "OBV MACD vs. Traditional MACD: 9,216
Backtests" (https://statoasis.com/overfit/research/obv-macd-vs-traditional-macd-which-one-wins,
visited via browser_exec this iteration): applying the classic MACD
construction (EMA(fast)-EMA(slow) vs its own EMA(signal)) to On-Balance
Volume instead of price ("OBV-MACD") and using it as a wholesale
REPLACEMENT for the traditional price-based MACD signal loses more often
than it wins (worse profit factor in 53.1% of 3,072 matched backtest
pairs). However, using OBV-MACD as a CONFIRMATION FILTER layered on top of
the traditional price MACD entry -- i.e. only take the price MACD
crossover signal when the OBV-MACD histogram already agrees (is positive
for a long entry) -- wins decisively: better profit factor in 67.3% of
pairs, better Sharpe in 64.2%, and a smaller worst drawdown in 85.7% of
pairs (at the cost of ~42% fewer trades). This is the "MACD+OBV" row from
the source's own three-way comparison, and is the specific construction
tested here -- distinct from both plain price MACD (already covered
extensively in this repo) and from Apirine's OBVM (2026-09-17-156, a
self-contained OBV-only signal-line-crossover, not a filter layered on a
separate price-MACD entry).

Signal logic
------------
- price_macd = EMA(close, fast) - EMA(close, slow); price_signal =
  EMA(price_macd, signal_len).
- obv = cumulative signed-volume running total (Granville's OBV: +volume
  on up days, -volume on down days, 0 on flat days).
- obv_macd = EMA(obv, fast) - EMA(obv, slow); obv_signal =
  EMA(obv_macd, signal_len) (identical MACD construction, applied to OBV).
- Entry (long): price_macd crosses above price_signal (the traditional
  MACD buy signal) AND obv_macd > obv_signal AT THE SAME BAR (OBV-MACD
  histogram already positive/in agreement -- the source's "confirmation
  gates entries only" rule, exit untouched).
- Exit: price_macd crosses below price_signal (mirrors the source's own
  unmodified MACD exit rule) OR max_hold_days time-stop (this repo's
  standard safety addition, not part of the bare source rule).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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


def _macd(series: pd.Series, fast: int, slow: int, signal_len: int):
    macd_line = series.ewm(span=fast, adjust=False).mean() - series.ewm(span=slow, adjust=False).mean()
    signal_line = macd_line.ewm(span=signal_len, adjust=False).mean()
    return macd_line, signal_line


def generate_signals(
    price_df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal_len: int = 9,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    price_macd, price_signal = _macd(close, fast, slow, signal_len)

    direction = np.sign(close.diff().fillna(0.0))
    signed_volume = direction * volume
    obv = signed_volume.cumsum()

    obv_macd, obv_signal = _macd(obv, fast, slow, signal_len)

    price_cross_up = (price_macd > price_signal) & (price_macd.shift(1) <= price_signal.shift(1))
    price_cross_down = (price_macd < price_signal) & (price_macd.shift(1) >= price_signal.shift(1))
    obv_confirms = obv_macd > obv_signal

    entry = (price_cross_up & obv_confirms).fillna(False)
    exit_signal = price_cross_down.fillna(False)

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
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
