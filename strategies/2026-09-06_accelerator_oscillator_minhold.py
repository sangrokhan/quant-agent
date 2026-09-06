"""Strategy: Accelerator Oscillator (AC) zero-line crossover with a
min-hold-days trade-frequency gate.

Direct fix for near-miss 2026-09-06-173 (Accelerator Oscillator zero-line
crossover + trend filter + ATR stop/target, QQQ Sharpe 0.927 barely
missed 1.0 threshold, both QQQ and SPY failed transaction-cost survival
at 366-373 trades over 11.7 years). Same fix pattern applied successfully
to Klinger Volume Oscillator (2026-09-04-085) and this cron trigger's own
ZLEMA crossover (2026-09-06-171): add an explicit min_hold_days gate that
suppresses the zero-line reverse-cross exit signal for the first N days
after entry -- the ATR stop-loss and take-profit still fire immediately
regardless of min_hold_days (they're risk-management, not signal noise),
only the crossover-based exit is delayed. This directly targets the
transaction-cost failure mode without changing the entry logic.

Signal logic (identical to 2026-09-06_accelerator_oscillator_trend.py
except for the min_hold_days gate on the crossover exit only)
------------------------------------------------------------------------
- median_price = (high + low) / 2
- ao = SMA(5, median_price) - SMA(34, median_price)
- ac = ao - SMA(5, ao)
- Entry (long): ac crosses from <=0 to >0 AND close > SMA(trend_window).
- Exit: ATR stop-loss or take-profit fire unconditionally at any time;
  the ac reverse zero-line cross only forces an exit once held >=
  min_hold_days; a max_hold_days time-stop is an absolute ceiling.

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
    trend_window: int = 100,
    atr_window: int = 14,
    atr_stop_mult: float = 1.5,
    atr_target_mult: float = 3.0,
    min_hold_days: int = 5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    median_price = (high + low) / 2.0

    ao = median_price.rolling(5).mean() - median_price.rolling(34).mean()
    ac = ao - ao.rolling(5).mean()

    ac_pos = ac > 0
    cross_up = ac_pos & (~ac_pos.shift(1).fillna(False))
    cross_down = (~ac_pos) & (ac_pos.shift(1).fillna(False))

    trend_sma = close.rolling(trend_window).mean()
    uptrend = close > trend_sma

    atr = _atr(df, atr_window)

    entry_signal = cross_up & uptrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_price = None
    target_price = None

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            c = close.iloc[i]
            stopped_out = stop_price is not None and c <= stop_price
            targeted_out = target_price is not None and c >= target_price
            crossover_exit = held >= min_hold_days and bool(cross_down.iloc[i])
            if stopped_out or targeted_out or crossover_exit or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]) and i > 0 and not pd.isna(atr.iloc[i]):
                in_position = True
                entry_idx = i
                prev_low = low.iloc[i - 1]
                prev_close = close.iloc[i - 1]
                stop_price = prev_low - atr_stop_mult * atr.iloc[i]
                target_price = prev_close + atr_target_mult * atr.iloc[i]
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 100,
    atr_window: int = 14,
    atr_stop_mult: float = 1.5,
    atr_target_mult: float = 3.0,
    min_hold_days: int = 5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Daily strategy returns: position (lagged by 1 bar to avoid
    lookahead) times the underlying daily simple return."""
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        trend_window=trend_window,
        atr_window=atr_window,
        atr_stop_mult=atr_stop_mult,
        atr_target_mult=atr_target_mult,
        min_hold_days=min_hold_days,
        max_hold_days=max_hold_days,
    )
    strat_returns = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_returns
