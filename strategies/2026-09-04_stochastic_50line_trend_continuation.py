"""Strategy: Classic Stochastic %K 50-line trend-continuation crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-163):
Rather than using the classic Stochastic Oscillator (%K/%D) for
overbought/oversold mean-reversion (already tested extensively in this
repo, e.g. 2026-09-04-028), a %K crossing above the 50 midline while price
is above a long-term trend SMA signals bullish momentum CONTINUATION
worth a long entry -- treating 50 as a directional-bias threshold rather
than 80/20 as reversal zones. Per FXGlory's own (honest, mostly-negative)
forex Stochastic strategy backtest article: among 4 tested variants
(K/D crossover, 50-line continuation, divergence, MA-pullback), the 50-line
continuation setup had the LEAST-negative expectancy of the four
(-0.1977R vs worse for the others), motivating a cleaner equity/crypto-bar
retest here with an explicit trend filter (their setup already required
"trend-aligned environment" but exact filter definition wasn't given).
Exit when %K crosses back below 50, or the trend filter breaks (close below
trend SMA), or a max_hold_days time-stop.

Signal logic
------------
- %K = 100 * (close - rolling_low(k_window)) / (rolling_high(k_window) -
  rolling_low(k_window)); %D = SMA(%K, d_window) (not used for entry here,
  computed for completeness/possible future use).
- Trend filter: close > SMA(trend_window).
- Entry (long): %K crosses above 50 AND close > SMA(trend_window) at that bar.
- Exit: %K crosses below 50, OR close crosses below SMA(trend_window), OR
  max_hold_days elapses since entry.
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and
grid_test.py: generate_signals/generate_returns take price_df plus keyword
params.
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


def _stochastic_k(df: pd.DataFrame, k_window: int) -> pd.Series:
    low_min = df["low"].rolling(k_window).min()
    high_max = df["high"].rolling(k_window).max()
    rng = (high_max - low_min).replace(0.0, np.nan)
    k = 100.0 * (df["close"] - low_min) / rng
    return k.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    k_window: int = 14,
    d_window: int = 3,
    trend_window: int = 100,
    midline: float = 50.0,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    k = _stochastic_k(df, k_window)
    trend_sma = close.rolling(trend_window).mean()

    cross_above_mid = (k > midline) & (k.shift(1) <= midline)
    cross_below_mid = (k < midline) & (k.shift(1) >= midline)
    trend_up = close > trend_sma
    trend_break = (close < trend_sma) & (close.shift(1) >= trend_sma.shift(1))

    entry_raw = cross_above_mid & trend_up
    exit_raw = cross_below_mid | trend_break

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_days = 0
    entry_arr = entry_raw.fillna(False).to_numpy()
    exit_arr = exit_raw.fillna(False).to_numpy()
    pos_arr = position.to_numpy().copy()

    for i in range(len(df)):
        if in_pos:
            hold_days += 1
            if exit_arr[i] or hold_days >= max_hold_days:
                in_pos = False
                hold_days = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if entry_arr[i]:
                in_pos = True
                hold_days = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    position = pd.Series(pos_arr, index=df.index, dtype=int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    k_window: int = 14,
    d_window: int = 3,
    trend_window: int = 100,
    midline: float = 50.0,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        k_window=k_window,
        d_window=d_window,
        trend_window=trend_window,
        midline=midline,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
