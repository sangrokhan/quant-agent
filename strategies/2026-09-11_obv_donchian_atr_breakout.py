"""Strategy: Donchian+OBV dual breakout with an ATR elevated-volatility filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-032):
Direct fix attempt for near-miss 2026-09-05-060 (plain Donchian price
breakout confirmed by a simultaneous OBV breakout: long when close breaks
above its own entry_window-day rolling high AND OBV breaks above its own
entry_window-day rolling high on the same bar). That entry's full-sample
Sharpe (0.906 SPY / 0.763 QQQ) missed the >=1.0 threshold despite passing
MDD/transaction-cost-survival/walk-forward.

Per PyQuantLab's "Catching Breakouts with OBV and ATR" (Oct 2025, visited
this iteration -- https://pyquantlab.medium.com/catching-breakouts-with-obv-and-atr-4dd891ff763e),
the source's own three-confirmation breakout rule adds a THIRD condition
beyond price+OBV: current ATR(atr_period) must exceed its own rolling
atr_lookback-day mean times atr_thresh_mult (default 1.2x) -- i.e. only
take the breakout when volatility is already elevated, explicitly to
filter out "false breakouts" that occur during quiet, low-volatility
periods. This is the new, testable, disclosed element added to the
existing near-miss's identical price+OBV breakout logic.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = close.diff().apply(lambda d: 1 if d > 0 else (-1 if d < 0 else 0))
    return (direction * volume).cumsum()


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def generate_signals(
    price_df: pd.DataFrame,
    entry_window: int = 20,
    exit_window: int = 10,
    atr_period: int = 14,
    atr_lookback: int = 20,
    atr_thresh_mult: float = 1.2,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry: close breaks above its own entry_window-day rolling high AND OBV
    breaks above its own entry_window-day rolling high (same bar) AND
    ATR(atr_period) > its own rolling atr_lookback-day mean * atr_thresh_mult
    (elevated-volatility confirmation, per PyQuantLab's OBV+ATR breakout).
    Exit: close falls below its own exit_window-day rolling low, or a
    max_hold_days time-stop.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=df.index)

    price_high = close.shift(1).rolling(entry_window).max()
    price_low_exit = close.shift(1).rolling(exit_window).min()

    obv = _obv(close, volume)
    obv_high = obv.shift(1).rolling(entry_window).max()

    atr = _atr(high, low, close, atr_period)
    atr_mean = atr.shift(1).rolling(atr_lookback).mean()

    entry_signal = (
        (close > price_high)
        & (obv > obv_high)
        & (atr > atr_mean * atr_thresh_mult)
    )
    exit_signal = close < price_low_exit

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    pos_vals = []
    for i in range(len(df)):
        if in_pos:
            hold_count += 1
            if bool(exit_signal.iloc[i]) or hold_count >= max_hold_days:
                in_pos = False
                hold_count = 0
        if not in_pos and bool(entry_signal.iloc[i]):
            in_pos = True
            hold_count = 0
        pos_vals.append(1 if in_pos else 0)
    position = pd.Series(pos_vals, index=df.index, dtype=int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
