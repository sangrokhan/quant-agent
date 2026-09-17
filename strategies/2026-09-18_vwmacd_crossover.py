"""Strategy: Volume-Weighted MACD (VW-MACD) signal-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-061):
Per LuxAlgo's "Volume-weighted MACD" library page
(https://www.luxalgo.com/library/indicator/volume-weighted-macd/): a MACD
variant built from Volume-Weighted Moving Averages (VWMA) instead of
EMAs -- every close is multiplied by its volume before averaging, so
high-volume bars drag the fast/slow lines harder while thin/low-volume
drift barely registers. The VW-MACD line is the 12-period fast VWMA minus
the 26-period slow VWMA, smoothed by a 9-period EMA signal line (same
canonical 12/26/9 spans as classic MACD). Source's disclosed trade rule:
"Signal-line crosses: volume-weighted momentum turning up or down, the
standard crossover grammar with participation built in." First
Volume-Weighted MACD strategy tested in this repo -- distinct from the
existing plain-EMA MACD entries (crossover, zeroline, divergence variants)
because the averaging itself is volume-weighted rather than exponential,
meaning high-participation moves are weighted more heavily than
low-volume drift within the same lookback window.

Signal logic
------------
- VWMA(n) = sum(close * volume, n) / sum(volume, n) (rolling volume-weighted
  average, standard construction).
- fast_vwma = VWMA(vwmacd_fast) [default 12]
- slow_vwma = VWMA(vwmacd_slow) [default 26]
- vwmacd_line = fast_vwma - slow_vwma
- signal_line = EMA(vwmacd_line, vwmacd_signal) [default 9]
- Entry (long): vwmacd_line crosses from <= signal_line to > signal_line
  (fresh bullish signal-line cross, per source's disclosed rule).
- Exit: vwmacd_line crosses back below signal_line, or a max_hold_days
  time-stop.
- Flat otherwise; long-only.

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


def _vwma(close: pd.Series, volume: pd.Series, window: int) -> pd.Series:
    pv = (close * volume).rolling(window).sum()
    v = volume.rolling(window).sum()
    return pv / v.replace(0, pd.NA)


def generate_signals(
    price_df: pd.DataFrame,
    vwmacd_fast: int = 12,
    vwmacd_slow: int = 26,
    vwmacd_signal: int = 9,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    fast_vwma = _vwma(close, volume, vwmacd_fast)
    slow_vwma = _vwma(close, volume, vwmacd_slow)
    vwmacd_line = (fast_vwma - slow_vwma).astype(float)
    signal_line = vwmacd_line.ewm(span=vwmacd_signal, adjust=False).mean()

    above = vwmacd_line > signal_line
    entry = above & (~above.shift(1).fillna(False))
    exit_cross = (~above) & (above.shift(1).fillna(False))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or held >= max_hold_days:
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
