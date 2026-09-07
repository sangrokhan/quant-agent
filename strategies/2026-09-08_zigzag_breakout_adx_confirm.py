"""Strategy: ZigZag resistance breakout confirmed by ADX +DI/-DI momentum.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-050):
Per theforexgeek.com's ZigZag Breakout Strategy: a ZigZag indicator (points
plotted only when price reverses by >= a percentage threshold, connected by
straight lines) identifies significant swing highs/lows while filtering
short-term noise. The prescribed buy rule: ZigZag shows a resistance level
(a swing high), price breaches that level (closes above it), ADX's +DI is
above -DI (uptrend direction), and ADX itself is above 20 (trend has
momentum). First ZigZag-based construction in this repo (0 prior hits) --
though ADX is used elsewhere, this specific ZigZag-swing-level-breakout +
ADX-momentum-confirmation combination has not been tested.

Signal logic
------------
- ZigZag pivots: a bar is a ZigZag high if price reverses down by >=
  zigzag_pct from that high before making a new higher high; symmetric for
  lows. Implemented via a simple forward-scan percentage-threshold algorithm
  (standard ZigZag construction).
- The most recent confirmed ZigZag high acts as the "resistance level".
- ADX, +DI, -DI computed via Wilder's standard method over adx_window.
- Entry (long): close breaks above the most recent confirmed ZigZag high
  (resistance breakout) AND +DI > -DI AND ADX > adx_threshold.
- Exit: after max_hold_days trading days, OR close falls back below the
  breakout level (invalidation stop), OR +DI crosses back below -DI
  (momentum reversal exit).
- Flat (no position) whenever not in an active long.

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


def _zigzag_highs(close: pd.Series, zigzag_pct: float) -> pd.Series:
    """Return a series aligned to close.index: at each bar i, the most
    recently CONFIRMED ZigZag swing-high value known as of bar i (NaN if
    none yet). A swing high is confirmed once price has reversed down by
    >= zigzag_pct from it."""
    vals = close.values
    n = len(vals)
    confirmed_high = np.full(n, np.nan)

    last_pivot_val = vals[0]
    last_pivot_idx = 0
    direction = 0  # 0 unknown, 1 up, -1 down
    last_confirmed_high = np.nan

    for i in range(1, n):
        confirmed_high[i] = last_confirmed_high
        change = (vals[i] - last_pivot_val) / last_pivot_val if last_pivot_val else 0.0
        if direction <= 0:
            # looking for an up move to confirm we're in an uptrend leg
            if change >= zigzag_pct:
                direction = 1
                last_pivot_val = vals[i]
                last_pivot_idx = i
            elif vals[i] < last_pivot_val:
                last_pivot_val = vals[i]
                last_pivot_idx = i
        if direction >= 0:
            if vals[i] > last_pivot_val and direction != -1:
                last_pivot_val = vals[i]
                last_pivot_idx = i
                direction = 1
            else:
                down_change = (vals[i] - last_pivot_val) / last_pivot_val if last_pivot_val else 0.0
                if direction == 1 and down_change <= -zigzag_pct:
                    # confirmed swing high at last_pivot_idx
                    last_confirmed_high = last_pivot_val
                    confirmed_high[i] = last_confirmed_high
                    direction = -1
                    last_pivot_val = vals[i]
                    last_pivot_idx = i

    return pd.Series(confirmed_high, index=close.index)


def _adx_di(df: pd.DataFrame, window: int) -> tuple[pd.Series, pd.Series, pd.Series]:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)

    atr = tr.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1 / window, adjust=False, min_periods=window).mean() / atr
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1 / window, adjust=False, min_periods=window).mean() / atr

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()

    return adx, plus_di, minus_di


def generate_signals(
    price_df: pd.DataFrame,
    zigzag_pct: float = 0.05,
    adx_window: int = 14,
    adx_threshold: float = 20.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    zz_resistance = _zigzag_highs(close, zigzag_pct)
    adx, plus_di, minus_di = _adx_di(df, adx_window)

    breakout = (close > zz_resistance.shift(1)) & zz_resistance.shift(1).notna()
    momentum_up = (plus_di > minus_di) & (adx > adx_threshold)

    entry = breakout & momentum_up.fillna(False)
    exit_momentum_flip = plus_di <= minus_di

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_level = -np.inf
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if (
                close.iloc[i] < stop_level
                or bool(exit_momentum_flip.iloc[i])
                or held >= max_hold_days
            ):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                stop_level = zz_resistance.shift(1).iloc[i]
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
