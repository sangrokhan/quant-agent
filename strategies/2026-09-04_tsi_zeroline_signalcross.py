"""Strategy: True Strength Index (TSI) zero-line entry + signal-line crossover exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-129):
William Blau's True Strength Index (TSI) is a double-smoothed momentum
oscillator: TSI = 100 * EMA(EMA(price momentum, r), s) / EMA(EMA(|price
momentum|, r), s), where price momentum is the 1-bar price change, r is
the long/first smoothing period (standard 25) and s is the
short/second smoothing period (standard 13). A signal line (EMA of TSI,
standard period 7) is used to time entries/exits. Per
enlightenedstocktrading.com's own systematic-rule example: "Enter a long
position when TSI crosses above the zero line ... Exit a long trade when
TSI crosses below the zero line." This strategy combines that zero-line
regime filter (only take signal-line crossover entries while TSI is above
zero, i.e. in a confirmed bullish momentum regime) with the signal-line
crossover as the more responsive entry/exit trigger within that regime --
first True Strength Index strategy tested in this repo, distinct from all
prior double-smoothed momentum oscillators (RVI computes vigor from
open/close range, not raw price momentum; PPO/MACD use fixed-length EMA
differences rather than Blau's double-EMA-of-momentum construction).

Signal logic
------------
- r: long EMA smoothing period for momentum (default 25).
- s: short EMA smoothing period for momentum (default 13).
- signal_period: EMA period for the TSI signal line (default 7).
- Long entry: TSI crosses above its signal line AND TSI > 0 (bullish
  momentum regime, per source's zero-line rule).
- Exit: TSI crosses below its signal line, OR TSI crosses below zero
  (source's own exit rule, trend-weakness signal), OR a max_hold_days
  time-stop.

Interface contract for validators (see validation/validators.py) and
grid_test.py: generate_signals/generate_returns take price_df plus keyword
params.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _tsi(close: pd.Series, r: int, s: int, signal_period: int) -> tuple[pd.Series, pd.Series]:
    momentum = close.diff()
    abs_momentum = momentum.abs()

    smoothed_momentum = momentum.ewm(span=r, adjust=False).mean().ewm(span=s, adjust=False).mean()
    smoothed_abs_momentum = abs_momentum.ewm(span=r, adjust=False).mean().ewm(span=s, adjust=False).mean()

    tsi = 100 * smoothed_momentum / smoothed_abs_momentum.replace(0, pd.NA)
    signal = tsi.ewm(span=signal_period, adjust=False).mean()
    return tsi, signal


def generate_signals(
    price_df: pd.DataFrame,
    r: int = 25,
    s: int = 13,
    signal_period: int = 7,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    tsi, signal = _tsi(close, r, s, signal_period)

    cross_up = (tsi > signal) & (tsi.shift(1) <= signal.shift(1))
    cross_down = (tsi < signal) & (tsi.shift(1) >= signal.shift(1))
    zero_cross_down = (tsi < 0) & (tsi.shift(1) >= 0)
    above_zero = tsi > 0

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_signal_cross = bool(cross_down.iloc[i]) if pd.notna(cross_down.iloc[i]) else False
            exit_zero_cross = bool(zero_cross_down.iloc[i]) if pd.notna(zero_cross_down.iloc[i]) else False
            if exit_signal_cross or exit_zero_cross or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            entry_cross = bool(cross_up.iloc[i]) if pd.notna(cross_up.iloc[i]) else False
            entry_regime = bool(above_zero.iloc[i]) if pd.notna(above_zero.iloc[i]) else False
            if entry_cross and entry_regime:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    r: int = 25,
    s: int = 13,
    signal_period: int = 7,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df, r=r, s=s, signal_period=signal_period, max_hold_days=max_hold_days
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
