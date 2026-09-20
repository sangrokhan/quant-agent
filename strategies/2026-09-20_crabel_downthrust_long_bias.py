"""Strategy: Toby Crabel "Down Thrust" traded LONG (counterintuitive per source's own data).

Hypothesis (see knowledge_base/strategies_log.jsonl):
Per Ali Casey's StatOasis 17,424-backtest study "Toby Crabel's Thrust Patterns"
(https://statoasis.com/overfit/research/unveiling-toby-crabel-s-up-down-thrust-trading-patterns):
Crabel's "down thrust" pattern (a pivot-low bar followed by a bar that opens
below the pivot low, closes above each of the previous two closes, and
closes in the UPPER half of its own range) is conventionally read as a
bearish reversal signal (short it). The source's own large-scale measurement
found the OPPOSITE: pooled across 8 markets, the down thrust "pays to the
upside" -- the next 20 bars averaged +0.94% vs +0.42% for an average day,
and traded short it was only a coin-flip (47.8% win rate across 938
settings). This strategy tests the source's own counterintuitive finding
directly: go LONG (not short) after a down-thrust bar, with the source's
own stated best-performing exit overlay -- an RSI(2) exit rule (source found
this reliably lifts win rate 50.0%->62.3% though its effect on net profit
is more mixed, 53.9% of pairs improved) -- plus a max_hold_days time-stop
backstop as this repo's addition. Distinct from all 3 prior "failed
breakdown" constructions in this repo (2026-09-04-076 Turtle Soup, plain
reclaim of an N-day low with no pivot/candle-shape structure;
2026-09-06-123 Wyckoff Spring, requires a detected accumulation range +
volume confirmation; 2026-09-10-001 Volume Profile VAL reclaim) -- this is
the first strategy using Crabel's specific pivot-low + open-below + 2-close
higher + upper-half-close candle structure.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, window: int = 2) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def _is_pivot_low(low: pd.Series, left: int, right: int) -> pd.Series:
    is_pivot = pd.Series(False, index=low.index)
    n = len(low)
    for i in range(left, n - right):
        window_low = low.iloc[i - left : i + right + 1]
        if low.iloc[i] == window_low.min() and (window_low == low.iloc[i]).sum() == 1:
            is_pivot.iloc[i] = True
    return is_pivot


def _detect_down_thrust(df: pd.DataFrame, pivot_left: int, pivot_right: int) -> pd.Series:
    """Down thrust: after a pivot low, a later bar opens below that pivot
    low, closes above each of the previous two closes, and closes in the
    upper half of its own high-low range."""
    low = df["low"]
    high = df["high"]
    close = df["close"]
    open_ = df["open"]

    is_pivot = _is_pivot_low(low, pivot_left, pivot_right)
    pivot_value = low.where(is_pivot).ffill()

    close_above_prev2 = (close > close.shift(1)) & (close > close.shift(2))
    range_mid = (high + low) / 2.0
    close_upper_half = close > range_mid
    opens_below_pivot = open_ < pivot_value

    down_thrust = opens_below_pivot & close_above_prev2 & close_upper_half
    return down_thrust.fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    pivot_left: int = 4,
    pivot_right: int = 2,
    rsi_window: int = 2,
    rsi_exit_level: float = 65.0,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    down_thrust = _detect_down_thrust(df, pivot_left, pivot_right)
    rsi = _rsi(df["close"], rsi_window)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(len(df)):
        if not in_pos:
            if bool(down_thrust.iloc[i]):
                in_pos = True
                hold_count = 0
        else:
            hold_count += 1
            if bool(rsi.iloc[i] > rsi_exit_level) or hold_count >= max_hold_days:
                in_pos = False
        position.iloc[i] = 1 if in_pos else 0

    return position.shift(1).fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    pivot_left: int = 4,
    pivot_right: int = 2,
    rsi_window: int = 2,
    rsi_exit_level: float = 65.0,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        pivot_left=pivot_left,
        pivot_right=pivot_right,
        rsi_window=rsi_window,
        rsi_exit_level=rsi_exit_level,
        max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change().fillna(0.0)
    return position * daily_returns
