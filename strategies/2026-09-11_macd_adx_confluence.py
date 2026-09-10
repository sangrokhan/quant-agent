"""Strategy: MACD Zero-Line Slope + ADX/DI Rising-Trend Confluence.

Hypothesis (2026-09-11-053): per Forex Tester's "MACD and ADX strategy: how
to ride the trend" (https://www.forextester.com/blog/macd-and-adx-strategy),
combining MACD's trend-reversal detection with ADX's trend-strength
confirmation filters out false signals better than either alone. Source's
disclosed buy rule: (1) MACD line is above the zero line AND rising
(positive slope), (2) +DI crosses above -DI (directional confirmation),
(3) ADX itself is rising (trend strengthening, not just present). Exit when
either the MACD slope turns negative or -DI crosses back above +DI. This is
distinct from every prior single-indicator MACD or ADX/DMI strategy in this
repo (2026-09-03-013 MACD zero-line-only, 2026-09-03-017 ADX/DMI crossover
threshold-only) by requiring all three conditions (MACD zero-line position
+ slope, DI crossover, ADX slope) simultaneously as a genuine confluence
signal, long-only per SAFETY.md.

Signal logic
------------
- macd_line, macd_signal via standard EMA(12)/EMA(26)/EMA(9).
- macd_bullish = macd_line > 0 AND macd_line rising (diff > 0 over
  macd_slope_window bars).
- plus_di, minus_di, adx via Wilder's DMI/ADX (14-period default).
- di_bullish_cross = plus_di crosses above minus_di within
  di_cross_lag_days.
- adx_rising = adx > adx.shift(adx_slope_window).
- Long entry (fresh) when macd_bullish AND di_bullish_cross AND adx_rising
  all true; long entry PERSISTS (state held) while macd_line stays > 0.
- Exit (flat) when macd_line turns non-positive OR minus_di crosses back
  above plus_di.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _wilder_dmi_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14):
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(0.0, index=high.index)
    minus_dm = pd.Series(0.0, index=high.index)
    plus_dm[(up_move > down_move) & (up_move > 0)] = up_move[(up_move > down_move) & (up_move > 0)]
    minus_dm[(down_move > up_move) & (down_move > 0)] = down_move[(down_move > up_move) & (down_move > 0)]

    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)

    atr = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)
    adx = dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    return plus_di, minus_di, adx


def generate_signals(
    price_df: pd.DataFrame,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal_span: int = 9,
    macd_slope_window: int = 3,
    dmi_period: int = 14,
    di_cross_lag_days: int = 3,
    adx_slope_window: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series per the MACD+ADX confluence rule."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    ema_fast = close.ewm(span=macd_fast, adjust=False).mean()
    ema_slow = close.ewm(span=macd_slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow

    macd_bullish = (macd_line > 0) & (macd_line.diff(macd_slope_window) > 0)
    macd_bearish_exit = macd_line <= 0

    plus_di, minus_di, adx = _wilder_dmi_adx(high, low, close, period=dmi_period)

    di_cross_up = (plus_di > minus_di) & (plus_di.shift(1) <= minus_di.shift(1))
    di_cross_up_recent = di_cross_up.rolling(di_cross_lag_days, min_periods=1).max().astype(bool)
    di_cross_down = (minus_di > plus_di) & (minus_di.shift(1) <= plus_di.shift(1))

    adx_rising = adx > adx.shift(adx_slope_window)

    entry_signal = macd_bullish & di_cross_up_recent & adx_rising.fillna(False)
    exit_signal = macd_bearish_exit | di_cross_down.fillna(False)

    state = pd.Series(index=close.index, dtype=float)
    state[entry_signal] = 1.0
    state[exit_signal] = 0.0
    state = state.ffill().fillna(0.0)
    return state.astype(int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
