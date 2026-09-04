"""Strategy: MACD line-vs-signal + RSI oversold-recovery dual confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-161):
RSI(14) recovering out of its oversold zone (crossing back above 30) while
the MACD(12,26,9) line is simultaneously above its signal line (bullish
momentum already confirmed) marks a higher-conviction long entry than either
indicator alone -- per TheForexGeek's RSI & MACD Strategy article's buy-rule
list ("RSI(14) around the oversold 30 zone" + "MACD histogram/line above
signal line"), and QuantifiedStrategies.com's MACD-and-RSI-Strategy article
(73% win rate over 235 trades on SMH, combining MACD+RSI+a third
mean-reversion filter, though its exact numeric rule is paywalled). This is
the FIRST strategy in this repo to combine RSI as an oversold-RECOVERY signal
(not a pure threshold cross) with a MACD trend/momentum confirmation filter
in a single joint-condition entry -- distinct from prior MACD-only
(2026-09-03-013, zero-line filter) and RSI-only (rsi2_meanrev, rsi_momentum
2026-09-04-077) tests already in this repo.

Signal logic
------------
- RSI(rsi_window) computed via Wilder's smoothing.
- MACD line = EMA(close, macd_fast) - EMA(close, macd_slow); signal line =
  EMA(MACD line, macd_signal).
- Entry (long): RSI crosses back above oversold_threshold (recovering from
  oversold, i.e. RSI[t-1] <= threshold and RSI[t] > threshold) AND MACD line
  is above its signal line at that same bar (bullish momentum already
  confirmed, not itself the trigger).
- Exit: RSI crosses above overbought_threshold, OR MACD line crosses below
  its signal line, OR max_hold_days elapses since entry.
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and
grid_test.py: generate_signals/generate_returns take price_df plus keyword
params.
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


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(50.0)
    return rsi


def _macd(close: pd.Series, fast: int, slow: int, signal: int) -> tuple[pd.Series, pd.Series]:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 14,
    oversold_threshold: float = 30.0,
    overbought_threshold: float = 70.0,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    rsi = _rsi(close, rsi_window)
    macd_line, signal_line = _macd(close, macd_fast, macd_slow, macd_signal)

    rsi_recover = (rsi > oversold_threshold) & (rsi.shift(1) <= oversold_threshold)
    macd_bullish = macd_line > signal_line
    macd_bearish_cross = (macd_line < signal_line) & (macd_line.shift(1) >= signal_line.shift(1))
    rsi_overbought_cross = (rsi > overbought_threshold) & (rsi.shift(1) <= overbought_threshold)

    entry_raw = rsi_recover & macd_bullish
    exit_raw = macd_bearish_cross | rsi_overbought_cross

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_days = 0
    entry_arr = entry_raw.fillna(False).to_numpy()
    exit_arr = exit_raw.fillna(False).to_numpy()
    pos_arr = position.to_numpy().copy()

    for i in range(len(df)):
        if in_pos:
            hold_days += 1
            if exit_arr[i] or hold_days >= max_hold_days:
                in_pos = False
                hold_days = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if entry_arr[i]:
                in_pos = True
                hold_days = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    position = pd.Series(pos_arr, index=df.index, dtype=int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    rsi_window: int = 14,
    oversold_threshold: float = 30.0,
    overbought_threshold: float = 70.0,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        rsi_window=rsi_window,
        oversold_threshold=oversold_threshold,
        overbought_threshold=overbought_threshold,
        macd_fast=macd_fast,
        macd_slow=macd_slow,
        macd_signal=macd_signal,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
