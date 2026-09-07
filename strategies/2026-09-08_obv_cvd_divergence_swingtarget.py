"""Strategy: OBV-as-cumulative-delta-proxy bullish divergence, swing-target exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-019):
Per pinescriptforge.com's Cumulative Delta Divergence strategy
(https://pinescriptforge.com/strategy/cumulative-delta-divergence, backtested
by the source across 64 futures symbols): "price makes a lower low while
cumulative delta makes a higher low" (bullish divergence) signals aggressive
selling is being absorbed by passive buyers, preceding a reversal. Source's
exact exit rule: "target: prior swing high/low. stop above/below the
divergence pivot." This repo has no true tick-level buy/sell volume split,
so OBV (cumulative +/-volume by daily close direction) is used as the
closest available cumulative-delta proxy (same "running total of directional
volume flow" concept, just daily-close-sign-based instead of trade-aggressor-
based). Distinct from 2026-09-04-088 (already-rejected OBV divergence variant,
which required price to cross back above a short EMA before entering and
exited on a fixed stop, not a swing-high target) via using the source's own
swing-pivot target/stop mechanics and immediate-on-confirmation entry instead
of an EMA filter.

Signal logic
------------
- Find local swing lows in `close` over a `pivot_window`-bar window (bar i is
  a swing low if it's the min of the window centered on i).
- Bullish divergence: at the most recent swing low (index j), price makes a
  LOWER low than the prior swing low (index k < j), while OBV makes a
  HIGHER low at j than at k (price/volume-flow disagreement).
- Entry (long): on the bar the newer swing low at j is confirmed (i.e.
  `pivot_window // 2` bars after j, once we can confirm it was indeed a
  local min) -- enter at that confirmation bar's close.
- Exit: target = the most recent prior SWING HIGH before j (source's "prior
  swing high" rule); stop = swing low at j minus `stop_atr_mult` * ATR
  (source's "stop beyond the divergence pivot"); else a `max_hold_days`
  time-stop.
- Flat otherwise. Long-only.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def _obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff().fillna(0.0))
    return (direction * volume).cumsum()


def _find_swing_lows(close: pd.Series, pivot_window: int) -> pd.Series:
    """Boolean series: True at bar i if close[i] is the min over
    [i-pivot_window, i+pivot_window] (confirmed only pivot_window bars later)."""
    half = pivot_window
    n = len(close)
    is_low = pd.Series(False, index=close.index)
    vals = close.values
    for i in range(half, n - half):
        window = vals[i - half : i + half + 1]
        if vals[i] == window.min():
            is_low.iloc[i] = True
    return is_low


def _find_swing_highs(close: pd.Series, pivot_window: int) -> pd.Series:
    half = pivot_window
    n = len(close)
    is_high = pd.Series(False, index=close.index)
    vals = close.values
    for i in range(half, n - half):
        window = vals[i - half : i + half + 1]
        if vals[i] == window.max():
            is_high.iloc[i] = True
    return is_high


def generate_signals(
    price_df: pd.DataFrame,
    pivot_window: int = 5,
    stop_atr_mult: float = 1.5,
    atr_window: int = 14,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close, volume = df["close"], df["volume"]
    n = len(df)

    obv = _obv(close, volume)
    atr = _atr(df, atr_window)
    swing_low = _find_swing_lows(close, pivot_window)
    swing_high = _find_swing_highs(close, pivot_window)

    swing_low_idxs = list(np.where(swing_low.values)[0])
    swing_high_idxs = list(np.where(swing_high.values)[0])

    position = pd.Series(0, index=df.index, dtype=int)

    in_position = False
    entry_idx = 0
    target = None
    stop = None

    # For each pair of consecutive swing lows, check bullish divergence and
    # generate an entry signal at the confirmation bar (swing_low_idx + pivot_window).
    entry_signals = {}
    for a, b in zip(swing_low_idxs, swing_low_idxs[1:]):
        price_lower_low = close.iloc[b] < close.iloc[a]
        obv_higher_low = obv.iloc[b] > obv.iloc[a]
        if price_lower_low and obv_higher_low:
            confirm_idx = b + pivot_window
            if confirm_idx >= n:
                continue
            # Prior swing high before b, for the target.
            prior_highs = [h for h in swing_high_idxs if h < b]
            if not prior_highs:
                continue
            target_price = close.iloc[prior_highs[-1]]
            if pd.isna(atr.iloc[confirm_idx]):
                continue
            stop_price = close.iloc[b] - stop_atr_mult * atr.iloc[confirm_idx]
            entry_signals[confirm_idx] = (target_price, stop_price)

    for i in range(n):
        if in_position:
            held = i - entry_idx
            hit_target = close.iloc[i] >= target
            hit_stop = close.iloc[i] <= stop
            if hit_target or hit_stop or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                target = stop = None
                continue
            position.iloc[i] = 1
            continue

        if i in entry_signals:
            in_position = True
            entry_idx = i
            target, stop = entry_signals[i]
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
