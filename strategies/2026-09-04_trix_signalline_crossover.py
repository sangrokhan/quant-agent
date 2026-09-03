"""Strategy: TRIX signal-line crossover with zero-line filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-038):
Per Google AI-overview + multiple technical-analysis sources (TradeTaurex,
LightningChart, WarriorTrading), TRIX (the rate-of-change of a
triple-smoothed EMA of closing prices, standard period 14-15) crossing
above its own signal line (a 9-period EMA of TRIX) generates a long entry
-- the triple smoothing filters out minor noise/choppy price action that
plagues simpler oscillators. Sources recommend an explicit zero-line
filter (only take longs when TRIX > 0) to align with a broader bullish
trend and reduce false signals in ranging markets. Long-only, per repo
convention (short-side signal-line-crosses-below-from-above not
implemented).

TRIX formula (standard params: trix_window=15, signal_window=9):
    ema1 = EMA(close, trix_window)
    ema2 = EMA(ema1, trix_window)
    ema3 = EMA(ema2, trix_window)
    TRIX = (ema3 / ema3.shift(1) - 1) * 100   # 1-bar rate of change of the triple EMA
    signal = EMA(TRIX, signal_window)

Signal logic
------------
- Entry (long): TRIX crosses above signal (fresh cross, not every bar
  TRIX stays above) AND TRIX > 0 (zero-line filter).
- Exit: TRIX crosses below signal.
- Flat otherwise; long-only, no shorting.

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


def _trix(close: pd.Series, trix_window: int) -> pd.Series:
    ema1 = close.ewm(span=trix_window, adjust=False).mean()
    ema2 = ema1.ewm(span=trix_window, adjust=False).mean()
    ema3 = ema2.ewm(span=trix_window, adjust=False).mean()
    trix = (ema3 / ema3.shift(1) - 1.0) * 100.0
    return trix


def generate_signals(
    price_df: pd.DataFrame,
    trix_window: int = 15,
    signal_window: int = 9,
    require_zero_line: bool = True,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    trix = _trix(close, trix_window)
    signal = trix.ewm(span=signal_window, adjust=False).mean()

    bullish_cross = (trix > signal) & (trix.shift(1) <= signal.shift(1))
    bearish_cross = (trix < signal) & (trix.shift(1) >= signal.shift(1))

    if require_zero_line:
        entry = bullish_cross & (trix > 0)
    else:
        entry = bullish_cross
    exit_signal = bearish_cross

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
