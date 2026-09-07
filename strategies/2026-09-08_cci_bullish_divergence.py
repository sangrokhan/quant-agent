"""Strategy: CCI Bullish Divergence.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-125):
Per https://www.avatrade.com/education/technical-analysis-indicators-strategies/cci-trading-strategies,
a bullish divergence occurs when price makes a LOWER low while the CCI
(Commodity Channel Index) oscillator makes a HIGHER low at the
corresponding point -- "the trend line on the price chart and the trend
line on the indicator are moving in the opposite directions" -- signaling
a high-probability trend reversal (the source states divergence signals
are "considered to be one of the strongest oscillator signals" precisely
because they occur "much less often" than simple threshold crosses, making
them more reliable). This is the FIRST CCI-divergence-specific strategy in
this repo -- prior CCI strategies (2026-09-04-024 oversold threshold cross,
2026-09-04-072 momentum breakout cross, 2026-09-04-145 WaveTrend
signal-line cross) all used raw threshold/crossover triggers, never a
divergence pattern between price and the oscillator's own trajectory.

Signal logic
------------
- CCI(cci_window) computed via the standard formula: (typical_price - SMA)
  / (0.015 * mean_absolute_deviation).
- Detect local price lows (a `low` value that is the minimum within a
  trailing `pivot_window`-bar lookback and hasn't been superseded since).
- Bullish divergence: comparing the CURRENT confirmed pivot low to the
  PRIOR confirmed pivot low -- price makes a lower low (current pivot low <
  prior pivot low) while CCI at the current pivot is higher than CCI at the
  prior pivot (higher low in the oscillator).
- Entry: long at the close of the bar where the divergence is confirmed
  (the current pivot's confirmation bar, `pivot_window` bars after the
  pivot itself, once we know it wasn't superseded).
- Exit: CCI crosses back above an overbought level (default +100), OR a
  max-holding-period time-stop.
- Flat otherwise, long-only, one position at a time.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _cci(df: pd.DataFrame, window: int) -> pd.Series:
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    sma = typical_price.rolling(window).mean()
    import numpy as np
    mad = typical_price.rolling(window).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    cci = (typical_price - sma) / (0.015 * mad.replace(0, pd.NA))
    return cci


def generate_signals(
    price_df: pd.DataFrame,
    cci_window: int = 20,
    pivot_window: int = 5,
    overbought_exit: float = 100.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close, low = df["close"], df["low"]
    cci = _cci(df, cci_window)

    # confirmed pivot low: low[i] is the min over [i-pivot_window, i+pivot_window]
    rolling_min = low.rolling(2 * pivot_window + 1, center=True).min()
    is_pivot_low = (low == rolling_min)

    # We only "know" a pivot at index i once we've seen pivot_window bars after it.
    n = len(close)
    prior_pivot_idx = None
    prior_pivot_low = None
    prior_pivot_cci = None
    entry_signal = pd.Series(False, index=close.index)

    for i in range(n):
        confirm_idx = i - pivot_window
        if confirm_idx < 0:
            continue
        if bool(is_pivot_low.iloc[confirm_idx]) and pd.notna(cci.iloc[confirm_idx]):
            cur_low = low.iloc[confirm_idx]
            cur_cci = cci.iloc[confirm_idx]
            if prior_pivot_idx is not None:
                if cur_low < prior_pivot_low and cur_cci > prior_pivot_cci:
                    entry_signal.iloc[i] = True
            prior_pivot_idx = confirm_idx
            prior_pivot_low = cur_low
            prior_pivot_cci = cur_cci

    exit_overbought = cci > overbought_exit

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_overbought.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
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
