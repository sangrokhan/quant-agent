"""Strategy: Volume Zone Oscillator (VZO) oversold-recovery, trend-gated.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-122):
The Volume Zone Oscillator (VZO, Walid Khalil & David Steckler,
2009/2011): VZO = 100 * (VP / TV), where TV (Total Volume) is an n-day
EMA of volume, and VP (Volume Position) is an n-day EMA of signed volume
(OBV-style: +volume if today's close > yesterday's close, else -volume).
Source (quantifiedstrategies.com) gives the explicit free rule: combine
VZO with an ADX(14) > 18 trend-strength filter and a 60-period EMA
trend-direction filter. In an uptrend (price > EMA60, ADX > 18), VZO
rising back above the -40% level from the oversold zone is a buy signal.
We implement this as a long-only strategy with a max_hold_days safety
time-stop (source's own exit rule for this cross isn't specified beyond
the entry trigger).

Formula
-------
VP[i] = EMA(vzo_period) of (volume[i] if close[i]>close[i-1] else -volume[i])
TV[i] = EMA(vzo_period) of volume[i]
VZO[i] = 100 * VP[i] / TV[i]

Signal logic
------------
- Trend filter: ADX(14) > adx_threshold AND close > EMA(trend_window).
- Entry (long): VZO crosses from <= oversold_level to > oversold_level
  (recovery from the oversold zone), AND the trend filter is true.
- Exit: trend filter turns false (ADX drops or price falls below EMA),
  OR a max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept params as keyword args.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _vzo(close: pd.Series, volume: pd.Series, period: int) -> pd.Series:
    signed_volume = volume.where(close > close.shift(1), -volume)
    vp = signed_volume.ewm(span=period, min_periods=period, adjust=False).mean()
    tv = volume.ewm(span=period, min_periods=period, adjust=False).mean()
    return 100.0 * vp / tv.replace(0, float("nan"))


def _adx(df: pd.DataFrame, period: int) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)

    atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean() / atr.replace(0, float("nan"))
    minus_di = 100 * minus_dm.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean() / atr.replace(0, float("nan"))

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, float("nan"))
    adx = dx.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    return adx


def generate_signals(
    price_df: pd.DataFrame,
    vzo_period: int = 14,
    oversold_level: float = -40.0,
    adx_period: int = 14,
    adx_threshold: float = 18.0,
    trend_window: int = 60,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"].astype(float)
    volume = df["volume"].astype(float)

    vzo = _vzo(close, volume, vzo_period)
    adx = _adx(df, adx_period)
    ema_trend = close.ewm(span=trend_window, min_periods=trend_window, adjust=False).mean()

    trend_ok = (adx > adx_threshold) & (close > ema_trend)

    vzo_prev = vzo.shift(1)
    cross_up_oversold = (vzo_prev <= oversold_level) & (vzo > oversold_level)

    entry = (cross_up_oversold & trend_ok).fillna(False)
    exit_signal = (~trend_ok).fillna(True)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
    close = df["close"].astype(float)
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
