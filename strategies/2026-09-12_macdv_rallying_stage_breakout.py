"""Strategy: MACD-V "Rallying" stage momentum breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Alex Spiroglou's MACD-V (2022, "MACD-V: Volatility Normalised Momentum",
NAAIM Founders Award / CMT Charles H. Dow Award) defines seven momentum
"stages" for the ATR-normalized MACD. Per
https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/macd-v
(exact source text): "Rallying. The market is rallying with strong upside
momentum when the MACD-V is between 150 and 50 (150 > X > 50) and above
its signal line." This repo already tested the "Rebounding" stage
(-150 < X < 50, capturing bounces off oversold lows -- id 2026-09-06-094,
accepted for equities). This iteration tests the DISTINCT "Rallying" stage
instead: long entry when MACD-V crosses above its signal line while
ALREADY inside the 50-150 momentum band (trend-continuation/breakout
read, not a bounce-off-lows read) -- i.e. buying strength confirmation
rather than buying a low. Exit on crossing back below signal, on exceeding
the "Risk" (overbought) threshold of 150, or falling back into the
"Ranging" band (<50, source's own regime label), plus a max_hold_days
time-stop backstop.

Construction: MACD-V = [(EMA(fast) - EMA(slow)) / ATR(atr_window)] * 100;
Signal = EMA(signal_span) of MACD-V. Long entry when MACD-V crosses above
Signal AND rally_low < MACD-V < rally_high (default 50/150, source's own
disclosed range). Exit when MACD-V crosses back below Signal, or drops
below rally_low, or a max_hold_days time-stop.

Distinct from 2026-09-06-094 (different momentum-stage zone: continuation
vs bounce -- economically a different edge, since "buy strength" and "buy
weakness reverting" are opposite trading philosophies even though built
from the identical underlying indicator).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)


def _macd_v(df: pd.DataFrame, fast: int, slow: int, atr_window: int) -> pd.Series:
    close = df["close"]
    ema_fast = close.ewm(span=fast, adjust=False, min_periods=fast).mean()
    ema_slow = close.ewm(span=slow, adjust=False, min_periods=slow).mean()
    tr = _true_range(df["high"], df["low"], close)
    atr = tr.ewm(span=atr_window, adjust=False, min_periods=atr_window).mean()
    macd_v = (ema_fast - ema_slow) / atr.replace(0.0, np.nan) * 100.0
    return macd_v


def generate_signals(
    price_df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    atr_window: int = 26,
    signal_span: int = 9,
    rally_low: float = 50.0,
    rally_high: float = 150.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    macd_v = _macd_v(df, fast, slow, atr_window)
    signal = macd_v.ewm(span=signal_span, adjust=False, min_periods=signal_span).mean()

    crossed_up = (macd_v > signal) & (macd_v.shift(1) <= signal.shift(1))
    crossed_down = (macd_v < signal) & (macd_v.shift(1) >= signal.shift(1))

    in_rally_zone = (macd_v > rally_low) & (macd_v < rally_high)
    entry_signal = (crossed_up & in_rally_zone).fillna(False).values
    exit_signal = (crossed_down | (macd_v <= rally_low) | (macd_v >= rally_high)).fillna(False).values

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_count = 0

    for i in range(len(df.index)):
        if in_position:
            hold_count += 1
            if exit_signal[i] or hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_signal[i]:
                in_position = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **params)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
