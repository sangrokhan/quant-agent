"""Strategy: HalfTrend dual-confirmation trend flip WITH an ATR-based hard
stop-loss (architectural fix attempt for crypto's catastrophic drawdown).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-036):
Direct architectural fix attempt for 2026-09-18-030 (HalfTrend dual-
confirmation flip on BTC/USDT and ETH/USDT, rejected -- every tested
amplitude/max_hold_days combination produced MDD > 0.57, because the base
strategy (strategies/2026-09-18_halftrend_dual_confirmation.py) has no
drawdown-control mechanism beyond the trend-flip exit and a time-stop).
This variant adds a hard ATR-multiple trailing stop-loss (the same general
technique already validated elsewhere in this repo, e.g. Chandelier Exit
constructions) on top of the identical, unmodified HalfTrend flip logic:
exit immediately (in addition to the existing flip/time-stop exits) if
price closes below (entry_price - atr_stop_mult * ATR(atr_period)) measured
from the entry bar, ratcheted upward as a trailing stop while in position.

Signal logic
------------
- amplitude, max_hold_days: identical to the parent HalfTrend strategy.
- atr_period: ATR lookback for the stop-loss (default 14).
- atr_stop_mult: ATR multiple for the trailing stop distance (default 3.0).
- Exit on: HalfTrend down-flip (parent's own exit rule), max_hold_days
  time-stop (parent's own exit rule), OR the new ATR trailing-stop being
  breached (close < running trailing stop level) -- whichever comes first.

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


def _atr(df: pd.DataFrame, length: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(length).mean()


def _halftrend_state(df: pd.DataFrame, amplitude: int) -> pd.Series:
    """Returns a boolean Series: True = uptrend, False = downtrend."""
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    close = df["close"].to_numpy(dtype=float)
    n = len(df)

    sma_high = df["high"].rolling(amplitude).mean().to_numpy(dtype=float)
    sma_low = df["low"].rolling(amplitude).mean().to_numpy(dtype=float)

    uptrend = np.empty(n, dtype=bool)
    running_max_low = low[0] if n else np.nan
    running_min_high = high[0] if n else np.nan
    trend_up = True

    for i in range(n):
        if i == 0:
            uptrend[i] = trend_up
            continue

        prior_low = low[i - 1]
        prior_high = high[i - 1]

        if trend_up:
            running_max_low = max(running_max_low, low[i]) if not np.isnan(running_max_low) else low[i]
        else:
            running_min_high = min(running_min_high, high[i]) if not np.isnan(running_min_high) else high[i]

        sh, sl = sma_high[i], sma_low[i]
        if trend_up and not np.isnan(sh):
            if sh < running_max_low and close[i] < prior_low:
                trend_up = False
                running_min_high = high[i]
        elif (not trend_up) and not np.isnan(sl):
            if sl > running_min_high and close[i] > prior_high:
                trend_up = True
                running_max_low = low[i]

        uptrend[i] = trend_up

    return pd.Series(uptrend, index=df.index)


def generate_signals(
    price_df: pd.DataFrame,
    amplitude: int = 2,
    max_hold_days: int = 20,
    atr_period: int = 14,
    atr_stop_mult: float = 3.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    uptrend = _halftrend_state(df, amplitude)
    atr = _atr(df, atr_period)

    flip_up = uptrend & (~uptrend.shift(1).fillna(uptrend.iloc[0] if len(uptrend) else True))
    flip_down = (~uptrend) & (uptrend.shift(1).fillna(uptrend.iloc[0] if len(uptrend) else True))

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    trailing_stop = -np.inf
    for i in range(n):
        c = close.iloc[i]
        a = atr.iloc[i]
        if in_pos:
            hold_count += 1
            # ratchet the trailing stop upward
            if pd.notna(a):
                candidate_stop = c - atr_stop_mult * a
                trailing_stop = max(trailing_stop, candidate_stop)
            exit_flip = bool(flip_down.iloc[i]) if pd.notna(flip_down.iloc[i]) else False
            exit_stop = c < trailing_stop
            if exit_flip or exit_stop or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
                trailing_stop = -np.inf
            else:
                position.iloc[i] = 1
        else:
            entry_now = bool(flip_up.iloc[i]) if pd.notna(flip_up.iloc[i]) else False
            if entry_now:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
                trailing_stop = (c - atr_stop_mult * a) if pd.notna(a) else -np.inf
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    amplitude: int = 2,
    max_hold_days: int = 20,
    atr_period: int = 14,
    atr_stop_mult: float = 3.0,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        amplitude=amplitude,
        max_hold_days=max_hold_days,
        atr_period=atr_period,
        atr_stop_mult=atr_stop_mult,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
