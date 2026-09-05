"""Strategy: Fisher Transform crossover, gated by a 50-period SMA trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-086),
sourced from https://enlightenedstocktrading.com/fisher-transform/
(Enlightened Stock Trading, "How to Use the Fisher Transform Indicator for
Smarter Trades"): the Ehlers Fisher Transform normalizes price into a
Gaussian-like distribution, sharpening turning points. The site's own
"Systematic Strategy Using the Fisher Transform" section gives explicit
trading rules:
    Buy: Fisher Transform crosses above its signal line from below -1.5,
         AND price is above its 50-period moving average.
    Sell: Fisher Transform crosses below its signal line from above +1.5,
          AND price is below its 50-period moving average.

This is a direct, source-grounded variation on the previously-REJECTED
Fisher Transform strategy (2026-09-04-051, decisive full-sample Sharpe fail,
-0.500 to 0.287 across 12 cells) which used ONLY the extreme-threshold
crossover with no trend filter at all. This iteration explicitly tests
whether adding the source's own recommended 50-period SMA trend-alignment
filter (long only when price > SMA50, short/flat only when price < SMA50)
fixes the prior version's decisive failure by avoiding counter-trend
whipsaw entries in choppy regimes -- the same "trend filter" pattern that
has repeatedly rescued other oscillator-crossover strategies in this repo
(e.g. Bollinger Band mean-reversion 2026-09-03-001 gated by vol regime,
IMI 2026-09-05-071 gated by SMA trend).

Signal logic
------------
- Fisher Transform: normalize close over `fisher_window` bars to [-1, 1]
  via the rolling min/max midpoint method, then apply the Ehlers Fisher
  transform 0.5*ln((1+x)/(1-x)), smoothed with a short EMA (`fisher_smooth`).
- Signal line = Fisher line shifted by 1 bar (the standard "trigger" line
  used in Ehlers' own reference implementation and reproduced by most
  retail sources including this one).
- Long entry: Fisher crosses above signal line, having been below
  `entry_threshold` (default -1.5) within the last 3 bars, AND close is
  above its `trend_window`-period SMA.
- Exit to flat: Fisher crosses below signal line (opposing crossover),
  OR close drops below the trend SMA (risk-off exit), OR after
  `max_hold_days` bars (avoid indefinite holds, consistent with this
  repo's other trend-filtered oscillator strategies).
- Long-only (no shorts) to keep this comparable to the repo's other
  equity/crypto long-only strategies and avoid the borrow-cost/short
  complications that aren't modeled by generate_returns' simple
  position-weighted math.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns, position lagged by 1 day to avoid look-ahead bias)
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


def _fisher_transform(close: pd.Series, window: int, smooth: int) -> pd.Series:
    roll_max = close.rolling(window, min_periods=window).max()
    roll_min = close.rolling(window, min_periods=window).min()
    rng = (roll_max - roll_min).replace(0, np.nan)

    # Normalize to [-0.999, 0.999] to keep the log() argument finite.
    raw = 2.0 * ((close - roll_min) / rng - 0.5)
    raw = raw.clip(-0.999, 0.999)

    fisher = 0.5 * np.log((1 + raw) / (1 - raw))
    fisher = fisher.ewm(span=smooth, adjust=False, min_periods=smooth).mean()
    return fisher


def generate_signals(
    price_df: pd.DataFrame,
    fisher_window: int = 9,
    fisher_smooth: int = 3,
    entry_threshold: float = -1.5,
    trend_window: int = 50,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fisher = _fisher_transform(close, fisher_window, fisher_smooth)
    signal_line = fisher.shift(1)

    sma_trend = close.rolling(trend_window, min_periods=trend_window).mean()
    above_trend = close > sma_trend

    crossed_up = (fisher > signal_line) & (fisher.shift(1) <= signal_line.shift(1))
    crossed_down = (fisher < signal_line) & (fisher.shift(1) >= signal_line.shift(1))

    was_extreme_low = (fisher.shift(1) < entry_threshold) | (fisher.shift(2) < entry_threshold) | (
        fisher.shift(3) < entry_threshold
    )

    entry_event = crossed_up & was_extreme_low.fillna(False) & above_trend.fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_count = 0
    entry_arr = entry_event.fillna(False).values
    exit_cross_arr = crossed_down.fillna(False).values
    above_trend_arr = above_trend.fillna(False).values

    for i in range(len(df.index)):
        if in_position:
            hold_count += 1
            if exit_cross_arr[i] or (not above_trend_arr[i]) or hold_count >= max_hold_days:
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
    # Shift position by 1 day: yesterday's signal determines today's exposure
    # (avoid look-ahead bias -- can't trade on today's own close).
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
