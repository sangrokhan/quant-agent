"""Strategy: Volume Weighted MACD (VW-MACD) signal-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-142):
Volume Weighted MACD replaces the standard MACD's fast/slow EMAs with
Volume-Weighted Moving Averages (VWMA), so the trend-momentum measure
itself incorporates volume (price moves on higher volume weigh more
heavily into the average) rather than treating volume as a separate
confirmation filter. Per Google's AI-overview synthesis of
TradingView/thinkorswim explainers: VW-MACD line = fast VWMA(12) - slow
VWMA(26); signal line = 9-period EMA of the VW-MACD line; histogram = VW-MACD
- signal. Canonical MACD-style systematic long entry: VW-MACD line crosses
above its signal line; exit on the opposite crossover, plus a
max_hold_days time-stop backstop. This is distinct from both (a) the
already-accepted plain VWMA dual-crossover (id 2026-09-04-060, fast VWMA vs
slow VWMA directly), and (b) the already-tested plain-EMA MACD variants --
here the MACD-style DIFFERENCE-and-signal-line construction is itself
volume-weighted, not just the underlying moving averages compared
head-to-head.

Signal logic
------------
- VWMA(window) = rolling sum(close*volume, window) / rolling
  sum(volume, window).
- vw_macd = VWMA(fast_window) - VWMA(slow_window).
- signal_line = EMA(vw_macd, signal_window).
- Entry (long): vw_macd crosses above signal_line.
- Exit: vw_macd crosses below signal_line, OR a max_hold_days time-stop
  backstop.
- Flat otherwise (long-only; no short leg per SAFETY.md scope).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _vwma(close: pd.Series, volume: pd.Series, window: int) -> pd.Series:
    pv = (close * volume).rolling(window).sum()
    v = volume.rolling(window).sum()
    return pv / v


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 12,
    slow_window: int = 26,
    signal_window: int = 9,
    max_hold_days: int = 25,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    fast_vwma = _vwma(close, volume, fast_window)
    slow_vwma = _vwma(close, volume, slow_window)
    vw_macd = fast_vwma - slow_vwma
    signal_line = vw_macd.ewm(span=signal_window, adjust=False).mean()

    cross_up = (vw_macd > signal_line) & (vw_macd.shift(1) <= signal_line.shift(1))
    cross_down = (vw_macd < signal_line) & (vw_macd.shift(1) >= signal_line.shift(1))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(cross_down.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]):
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
