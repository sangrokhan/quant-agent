"""Strategy: Toby Crabel "Up Thrust" traded LONG (source's own headline construction).

Hypothesis (see knowledge_base/strategies_log.jsonl):
Per Ali Casey's StatOasis 17,424-backtest study "Toby Crabel's Thrust
Patterns" (https://statoasis.com/overfit/research/unveiling-toby-crabel-s-up-
down-thrust-trading-patterns): the "up thrust" pattern is a pivot-high bar
(highest of pivot_left bars back / pivot_right bars forward) followed later
by a bar that opens ABOVE that pivot high, closes BELOW each of the previous
two closes, and closes in the LOWER half of its own high-low range --
visually a failed breakout / bearish-looking candle. The source's own
headline finding is nonetheless to buy the next open (source's own stated
rule), holding for a fixed bar count (10-bar headline hold tested). Source
measured only a small incremental edge over a random-entry control (1,182
up thrusts averaged +0.39% over the next 10 bars vs +0.29% for an average
day; a seeded random entry with the same hold beat the up-thrust long on
4 of 8 markets), so this is a deliberately marginal/skeptical hypothesis
test, not a strong-edge claim -- included per RESEARCH_LOOP.md's instruction
to ground hypotheses in what was actually read, not invent only "sure
things". This is distinct from the down-thrust-long test already run this
cron trigger (2026-09-20-145, rejected 0/144) and from the unrelated
Wyckoff Upthrust distribution-range short strategy already in this repo
(2026-09-08-039) -- Crabel's up thrust uses a pivot-HIGH + open-above +
2-close-lower + lower-half-close structure with no consolidation-range
detection requirement.

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


def _is_pivot_high(high: pd.Series, left: int, right: int) -> pd.Series:
    is_pivot = pd.Series(False, index=high.index)
    n = len(high)
    for i in range(left, n - right):
        window_high = high.iloc[i - left : i + right + 1]
        if high.iloc[i] == window_high.max() and (window_high == high.iloc[i]).sum() == 1:
            is_pivot.iloc[i] = True
    return is_pivot


def _detect_up_thrust(df: pd.DataFrame, pivot_left: int, pivot_right: int) -> pd.Series:
    """Up thrust: after a pivot high, a later bar opens above that pivot
    high, closes below each of the previous two closes, and closes in the
    lower half of its own high-low range."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    open_ = df["open"]

    is_pivot = _is_pivot_high(high, pivot_left, pivot_right)
    pivot_value = high.where(is_pivot).ffill()

    close_below_prev2 = (close < close.shift(1)) & (close < close.shift(2))
    range_mid = (high + low) / 2.0
    close_lower_half = close < range_mid
    opens_above_pivot = open_ > pivot_value

    up_thrust = opens_above_pivot & close_below_prev2 & close_lower_half
    return up_thrust.fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    pivot_left: int = 4,
    pivot_right: int = 2,
    max_hold_days: int = 10,
    use_rsi_exit: bool = True,
    rsi_window: int = 2,
    rsi_exit_level: float = 65.0,
) -> pd.Series:
    df = _prep(price_df)
    up_thrust = _detect_up_thrust(df, pivot_left, pivot_right)
    rsi = _rsi(df["close"], rsi_window) if use_rsi_exit else None

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(len(df)):
        if not in_pos:
            if bool(up_thrust.iloc[i]):
                in_pos = True
                hold_count = 0
        else:
            hold_count += 1
            rsi_exit = bool(rsi.iloc[i] > rsi_exit_level) if use_rsi_exit else False
            if rsi_exit or hold_count >= max_hold_days:
                in_pos = False
        position.iloc[i] = 1 if in_pos else 0

    return position.shift(1).fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    pivot_left: int = 4,
    pivot_right: int = 2,
    max_hold_days: int = 10,
    use_rsi_exit: bool = True,
    rsi_window: int = 2,
    rsi_exit_level: float = 65.0,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        pivot_left=pivot_left,
        pivot_right=pivot_right,
        max_hold_days=max_hold_days,
        use_rsi_exit=use_rsi_exit,
        rsi_window=rsi_window,
        rsi_exit_level=rsi_exit_level,
    )
    daily_returns = df["close"].pct_change().fillna(0.0)
    return position * daily_returns
