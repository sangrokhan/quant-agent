"""Strategy: Schaff Trend Cycle (STC) oversold-recovery crossover + trend gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-088),
sourced from https://quantstrategy.io/blog/understanding-the-schaff-trend-cycle-stc-indicator/
(QuantStrategy.io, "Understanding the Schaff Trend Cycle (STC) Indicator").
The source describes STC (Doug Schaff; MACD(23,50) fed through a
stochastic-of-MACD normalization, smoothed twice with 3-period SMAs into
a cycle line + signal line, oscillating 0-100) and gives two distinct
trading modes:
    1. Trend following: STC/signal crossover, in alignment with the
       broader trend.
    2. Overbought/oversold: STC entering extreme zones (>75 / <25)
       flags potential reversal points, best combined with a trend filter
       (source explicitly recommends "a 50-period or 100-period moving
       average to ensure your STC trades align with the major trend").

This iteration combines BOTH modes into a single testable rule, distinct
from the already-tested/accepted (SPY only) plain centerline-crossover
variant (2026-09-04-080, STC crossing above 50 = long, no oversold gate,
no trend filter): entry requires the STC line to cross above its signal
line WHILE recovering from the oversold zone (having dipped below 25
recently), AND price above a trend SMA -- an oversold-recovery-in-trend
setup rather than an unconditional centerline cross.

Signal logic
------------
- MACD(23,50) on close, EMA-based.
- Stochastic-of-MACD: %K = (MACD - rolling_min(MACD, stoch_window)) /
  (rolling_max(MACD, stoch_window) - rolling_min(MACD, stoch_window)) * 100
- STC cycle line = 3-period SMA of %K; STC signal line = 3-period SMA of
  the cycle line (matches source's calculation steps).
- Long entry: STC crosses above its signal line, having dipped below
  `oversold_threshold` (25) within the last 5 bars, AND close above its
  `trend_window`-period SMA.
- Exit: STC crosses below its signal line (opposite crossover), OR STC
  reaches `overbought_threshold` (75, take-profit per source's
  overbought-zone guidance), OR trend filter breaks, OR after
  `max_hold_days` (repo-standard safety time-stop).

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns, position lagged by 1 day to avoid look-ahead bias)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _schaff_trend_cycle(
    close: pd.Series,
    fast_span: int = 23,
    slow_span: int = 50,
    stoch_window: int = 10,
    smooth_span: int = 3,
) -> tuple[pd.Series, pd.Series]:
    macd = close.ewm(span=fast_span, adjust=False).mean() - close.ewm(span=slow_span, adjust=False).mean()

    roll_min = macd.rolling(stoch_window, min_periods=stoch_window).min()
    roll_max = macd.rolling(stoch_window, min_periods=stoch_window).max()
    rng = (roll_max - roll_min).replace(0, pd.NA)
    pct_k = ((macd - roll_min) / rng * 100).astype(float)

    cycle = pct_k.rolling(smooth_span, min_periods=smooth_span).mean()
    signal = cycle.rolling(smooth_span, min_periods=smooth_span).mean()
    return cycle, signal


def generate_signals(
    price_df: pd.DataFrame,
    fast_span: int = 23,
    slow_span: int = 50,
    stoch_window: int = 10,
    oversold_threshold: float = 25.0,
    overbought_threshold: float = 75.0,
    trend_window: int = 100,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    cycle, signal = _schaff_trend_cycle(close, fast_span, slow_span, stoch_window)

    sma_trend = close.rolling(trend_window, min_periods=trend_window).mean()
    above_trend = close > sma_trend

    crossed_up = (cycle > signal) & (cycle.shift(1) <= signal.shift(1))
    crossed_down = (cycle < signal) & (cycle.shift(1) >= signal.shift(1))
    was_oversold = (
        (cycle.shift(1) < oversold_threshold)
        | (cycle.shift(2) < oversold_threshold)
        | (cycle.shift(3) < oversold_threshold)
        | (cycle.shift(4) < oversold_threshold)
        | (cycle.shift(5) < oversold_threshold)
    )
    reached_overbought = cycle >= overbought_threshold

    entry_event = crossed_up.fillna(False) & was_oversold.fillna(False) & above_trend.fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_count = 0
    entry_arr = entry_event.values
    exit_cross_arr = crossed_down.fillna(False).values
    overbought_arr = reached_overbought.fillna(False).values
    above_trend_arr = above_trend.fillna(False).values

    for i in range(len(df.index)):
        if in_position:
            hold_count += 1
            if exit_cross_arr[i] or overbought_arr[i] or (not above_trend_arr[i]) or hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_arr[i]:
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
