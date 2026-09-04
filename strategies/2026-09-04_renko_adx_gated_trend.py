"""Strategy: ATR-brick Renko trend-following + 200-SMA filter + ADX>25 gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-087):
Direct follow-up to the rejected 2026-09-04-086 (ATR-brick Renko trend
following): that strategy's grid showed 0/48 passing cells in high-vol
regimes and a full-sample Sharpe (best 0.806) just short of the 1.0
threshold -- consistent with whipsaw losses during choppy/high-vol
periods dragging down an otherwise-workable trend signal. Per
Pomegra.io/FXNX/PyQuantLab's standard ADX filter guidance: ADX < 20-25
indicates a weak/absent trend where trend-following whipsaws; gating
entries to require ADX > 25 (a "strong trend present" reading) should
filter out exactly the choppy conditions that were dragging down the
prior version, without touching the core Renko-brick/200-SMA signal
logic itself.

Signal logic
------------
Identical Renko-brick + 200-SMA construction as
2026-09-04_renko_atr_trend_follow.py, with one addition:
- Compute Wilder's ADX(adx_window) from the standard +DI/-DI construction.
- Entry requires ADX > adx_threshold (default 25) in addition to the
  original entry conditions (above 200-SMA, N consecutive up-bricks).
- Exit logic unchanged (first down-brick or trend-filter break) --
  positions already open are not force-closed just because ADX later
  drops below the threshold (that would re-introduce whipsaw exits);
  the filter only gates NEW entries.

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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def _adx(df: pd.DataFrame, window: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    prev_high = high.shift(1)
    prev_low = low.shift(1)

    up_move = high - prev_high
    down_move = prev_low - low
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    plus_dm = pd.Series(plus_dm, index=df.index)
    minus_dm = pd.Series(minus_dm, index=df.index)

    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)

    atr = tr.ewm(alpha=1 / window, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / window, adjust=False).mean() / atr.replace(0, np.nan)
    minus_di = 100 * minus_dm.ewm(alpha=1 / window, adjust=False).mean() / atr.replace(0, np.nan)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1 / window, adjust=False).mean()
    return adx.fillna(0.0)


def _renko_bricks(close: pd.Series, brick_size: pd.Series) -> pd.Series:
    n = len(close)
    directions = pd.Series(0, index=close.index, dtype=int)
    level = None
    for i in range(n):
        c = close.iloc[i]
        bs = brick_size.iloc[i]
        if pd.isna(bs) or bs <= 0 or pd.isna(c):
            continue
        if level is None:
            level = c
            continue
        if c >= level + bs:
            directions.iloc[i] = 1
            steps = int((c - level) // bs)
            level = level + steps * bs
        elif c <= level - bs:
            directions.iloc[i] = -1
            steps = int((level - c) // bs)
            level = level - steps * bs
    return directions


def generate_signals(
    price_df: pd.DataFrame,
    atr_window: int = 14,
    trend_window: int = 200,
    confirm_bricks: int = 2,
    adx_window: int = 14,
    adx_threshold: float = 25.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    brick_size = _atr(df, atr_window)
    brick_dir = _renko_bricks(close, brick_size)
    adx = _adx(df, adx_window)

    sma = close.rolling(trend_window).mean()
    above_trend = close > sma

    last_dir = brick_dir.replace(0, np.nan).ffill().fillna(0)
    dir_change = last_dir != last_dir.shift(1)
    run_id = dir_change.cumsum()
    run_length = last_dir.groupby(run_id).cumcount() + 1

    strong_trend = adx > adx_threshold
    entry_trigger = (last_dir == 1) & (run_length >= confirm_bricks) & above_trend & strong_trend
    exit_trigger = (last_dir == -1) | (~above_trend)

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    for i in range(n):
        if in_pos:
            if bool(exit_trigger.iloc[i]):
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
                in_pos = True
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    atr_window: int = 14,
    trend_window: int = 200,
    confirm_bricks: int = 2,
    adx_window: int = 14,
    adx_threshold: float = 25.0,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        atr_window=atr_window,
        trend_window=trend_window,
        confirm_bricks=confirm_bricks,
        adx_window=adx_window,
        adx_threshold=adx_threshold,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
