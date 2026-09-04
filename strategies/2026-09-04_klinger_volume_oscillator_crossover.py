"""Strategy: Klinger Volume Oscillator (KVO) signal-line crossover with EMA trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-084):
Stephen Klinger's Volume Oscillator (KVO) computes a "volume force" term
from the day's high/low/close trend direction and volume, then takes the
difference of a fast and slow EMA of that volume-force series, further
smoothed by a signal-line EMA. Per Google's AI-overview summary of
LightningChart/EnlightenedStockTrading sources: a long entry triggers
when the KVO line crosses above its signal line (ideally with both below
the zero line, for early momentum), confirmed by a 50-period EMA trend
filter (price trading above the EMA); exit when KVO crosses back below
its signal line or turns negative. Distinct from every previously-tested
volume-based strategy in this repo (OBV -027, CMF -???, MFI -???, VWMA
-060) because it's specifically a volume-FORCE oscillator with its own
signal-line smoothing (structurally analogous to MACD, but volume-force
derived rather than price-EMA derived).

Signal logic
------------
- daily_trend[t] = +1 if (high+low+close)[t] > (high+low+close)[t-1] else -1
  (Klinger's own trend-direction rule, using the sum of H+L+C as the trend
  proxy)
- volume_force[t] = volume[t] * daily_trend[t] * abs(2 * ((close-low) -
  (high-close)) / (high-low)) * 100  (a simplified/commonly-used version
  of Klinger's volume-force formula)
- KVO = EMA(volume_force, fast_span) - EMA(volume_force, slow_span)
- signal_line = EMA(KVO, signal_span)
- ema_trend = EMA(close, ema_window)
- Entry (long): KVO crosses above signal_line AND close > ema_trend
  (trend filter).
- Exit: KVO crosses back below signal_line, OR close drops below
  ema_trend.
- Long-only, flat otherwise.

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


def _compute_kvo(df: pd.DataFrame, fast_span: int, slow_span: int, signal_span: int):
    high = df["high"]
    low = df["low"]
    close = df["close"]
    volume = df["volume"]

    hlc_sum = high + low + close
    trend = np.sign(hlc_sum.diff()).replace(0, np.nan).ffill().fillna(1.0)

    hl_range = (high - low).replace(0, np.nan)
    dm = ((close - low) - (high - close)) / hl_range
    dm = dm.fillna(0.0)
    volume_force = volume * trend * (2 * dm).abs() * 100

    kvo = volume_force.ewm(span=fast_span, adjust=False).mean() - volume_force.ewm(
        span=slow_span, adjust=False
    ).mean()
    signal_line = kvo.ewm(span=signal_span, adjust=False).mean()
    return kvo, signal_line


def generate_signals(
    price_df: pd.DataFrame,
    fast_span: int = 34,
    slow_span: int = 55,
    signal_span: int = 13,
    ema_window: int = 50,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    kvo, signal_line = _compute_kvo(df, fast_span, slow_span, signal_span)
    ema_trend = close.ewm(span=ema_window, adjust=False).mean()

    above_signal = kvo > signal_line
    above_signal_prev = above_signal.shift(1)
    cross_up = above_signal & (~above_signal_prev.fillna(False))
    cross_down = (~above_signal) & (above_signal_prev.fillna(False))

    above_trend = close > ema_trend

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    for i in range(n):
        if in_pos:
            if bool(cross_down.iloc[i]) or not bool(above_trend.iloc[i]):
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]) and bool(above_trend.iloc[i]):
                in_pos = True
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    fast_span: int = 34,
    slow_span: int = 55,
    signal_span: int = 13,
    ema_window: int = 50,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df, fast_span=fast_span, slow_span=slow_span, signal_span=signal_span, ema_window=ema_window
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
