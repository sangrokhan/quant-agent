"""Strategy: Chande QStick zero-cross, gated by an ADX(14)>threshold trend
filter (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-077):
Per a Google AI-overview synthesis (GoCharting-sourced), the Chande QStick
indicator (Tushar Chande) -- an EMA of (Close-Open), measuring candlestick
body-direction momentum -- crossing above zero signals bulls taking control;
when gated by a Wilder ADX(14) > threshold trend-strength filter (only take
the cross when a genuine trend is present, not a choppy/ranging market),
this should improve on the plain Qstick zero-cross already rejected in this
repo (2026-09-04-136, decisive fail, no trend-strength gate). Long-only per
SAFETY.md (source's own rule is long/short-symmetric).

Signal logic
------------
- Raw QStick = Close - Open; QStick(n) = EMA(Raw QStick, n).
- ADX(adx_period), Wilder's standard construction.
- Entry (long): QStick crosses from <=0 to >0 (fresh bullish cross) AND
  ADX > adx_threshold at that bar (trending regime confirmed).
- Exit: QStick crosses back below 0, OR a max_hold_days time-stop backstop
  (source gives no explicit time-stop, but repo convention requires one).
- Flat otherwise; long-only, no shorting.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly across a parameter grid).
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


def _true_range(df: pd.DataFrame) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    return pd.concat(
        [(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)


def _adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low = df["high"], df["low"]
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)

    tr = _true_range(df)
    atr = tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()

    plus_di = 100.0 * plus_dm.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean() / atr.replace(0, np.nan)
    minus_di = 100.0 * minus_dm.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean() / atr.replace(0, np.nan)

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    return adx


def generate_signals(
    price_df: pd.DataFrame,
    qstick_period: int = 14,
    adx_period: int = 14,
    adx_threshold: float = 25.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]

    raw_qstick = close - open_
    qstick = raw_qstick.ewm(span=qstick_period, adjust=False, min_periods=qstick_period).mean()
    adx = _adx(df, adx_period)

    prev_qstick = qstick.shift(1)
    bullish_cross = (qstick > 0) & (prev_qstick <= 0)
    bearish_cross = (qstick < 0) & (prev_qstick >= 0)
    trending = adx > adx_threshold

    entry = bullish_cross & trending.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(bearish_cross.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
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
