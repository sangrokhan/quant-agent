"""Strategy: Aroon Oscillator zero-line crossover gated by an SMA trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-092):
Per https://arrowalgo.com/aroon-oscillator-complete-guide-algorithmic-trading/'s
"Zero-line crossover strategy": "Enter long when the Aroon Oscillator crosses
above zero and price is above a longer-period moving average. Exit when the
Oscillator crosses back below zero." The Aroon Oscillator (AroonUp -
AroonDown over a rolling lookback, default 25) captures whether recent highs
(bullish) or recent lows (bearish) dominate; combining its zero-line cross
with a price>SMA trend filter is the source's own explicit combination for
"reducing false signals in choppy conditions" versus the raw oscillator
cross alone.

This is distinct from four prior Aroon-family entries already in this
repo's knowledge base: 2026-09-04-031 (Aroon-Down single-line absolute
threshold, no oscillator difference), 2026-09-04-063 (Aroon Oscillator
zero-cross alone, no trend filter), 2026-09-05-079 (dual-line simultaneous
70/30 threshold state, no crossover event), and 2026-09-06-098 (AroonUp/Down
crossover event + ADX filter, not the oscillator-difference zero-cross +
SMA-trend-filter combination tested here).

Signal logic
------------
- AroonUp[t] = 100 * (window - periods_since_highest_high) / window
- AroonDown[t] = 100 * (window - periods_since_lowest_low) / window
- Aroon Oscillator = AroonUp - AroonDown, range [-100, 100].
- Entry (long): Oscillator crosses from <=0 to >0 AND close > SMA(trend_window).
- Exit: Oscillator crosses back from >0 to <=0, OR the trend filter breaks
  (close <= SMA(trend_window)), OR a max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _aroon_oscillator(high: pd.Series, low: pd.Series, window: int) -> pd.Series:
    periods_since_high = high.rolling(window + 1).apply(
        lambda s: window - s.argmax(), raw=True
    )
    periods_since_low = low.rolling(window + 1).apply(
        lambda s: window - s.argmin(), raw=True
    )
    aroon_up = 100 * (window - periods_since_high) / window
    aroon_down = 100 * (window - periods_since_low) / window
    return aroon_up - aroon_down


def generate_signals(
    price_df: pd.DataFrame,
    aroon_window: int = 25,
    trend_sma_window: int = 50,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    osc = _aroon_oscillator(high, low, aroon_window)
    trend_sma = close.rolling(trend_sma_window).mean()
    trend_ok = close > trend_sma

    osc_prev = osc.shift(1)
    cross_up = (osc_prev <= 0) & (osc > 0)
    cross_down = (osc_prev > 0) & (osc <= 0)

    entry = cross_up & trend_ok.fillna(False)
    exit_cross = cross_down
    exit_trend = ~trend_ok.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or bool(exit_trend.iloc[i]) or held >= max_hold_days:
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
