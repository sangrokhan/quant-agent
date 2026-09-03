"""Strategy: Elder Impulse System (long-only, impulse-reversal exit).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-064):
Per Alexander Elder's Impulse System (Google AI-overview synthesis): a
13-period EMA and the MACD Histogram (standard 12/26/9) together classify
each bar as green (bullish impulse: both EMA slope AND MACD histogram
slope positive), red (bearish impulse: both negative), or blue/neutral
(mixed). Long entry on the close of a green bar; exit immediately when the
bar changes away from green (to blue or red) -- the "impulse reversal"
exit, the simpler of two documented exit variants.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _macd_histogram(close: pd.Series, fast: int, slow: int, signal: int) -> pd.Series:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line - signal_line


def generate_signals(
    price_df: pd.DataFrame,
    ema_window: int = 13,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ema = close.ewm(span=ema_window, adjust=False).mean()
    hist = _macd_histogram(close, macd_fast, macd_slow, macd_signal)

    ema_rising = ema > ema.shift(1)
    hist_rising = hist > hist.shift(1)
    ema_falling = ema < ema.shift(1)
    hist_falling = hist < hist.shift(1)

    green = ema_rising & hist_rising
    red = ema_falling & hist_falling
    # blue = ~green & ~red (implicit)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    for i in range(len(df)):
        if in_position:
            if not bool(green.iloc[i]):  # bar turned blue or red -> exit
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(green.iloc[i]):
                in_position = True
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
