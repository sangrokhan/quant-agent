"""Strategy: Accumulation/Distribution (A/D) Line bullish-divergence long entry.

Hypothesis (knowledge_base id 2026-09-06-A see strategies_log.jsonl):
Per TrendSpider's "Accumulation/Distribution (A/D) Trading Strategies" guide
(https://trendspider.com/learning-center/accumulation-distribution-a-d-trading-strategies/):
"A bullish divergence occurs when the price of a security is making lower
lows, but the A/D line is making higher lows. This suggests that buying
pressure is increasing even though the price is decreasing, which could
signal a potential reversal to the upside."

This is the first strategy in this repo built on the classic Chaikin
Accumulation/Distribution Line (a cumulative volume*CLV indicator), distinct
from all previously-tested price-divergence strategies (RSI Failure Swing,
Elder-Ray Bull Power) which used momentum/oscillator lines rather than a
volume-flow line -- the economic rationale here is specifically about
institutional buying pressure showing up in volume before price confirms it.

Signal logic
------------
- A/D Line = cumulative sum of Money Flow Volume, where
  CLV_t = ((close_t - low_t) - (high_t - close_t)) / (high_t - low_t)
  (Close Location Value, in [-1, 1]), Money Flow Volume_t = CLV_t * volume_t.
- Identify local swing lows in price (a close that is the minimum within a
  trailing `swing_window` bar window) and compare consecutive swing lows:
  bullish divergence = price swing low is LOWER than the prior price swing
  low, while the A/D line's value at the same bar is HIGHER than the A/D
  line's value at the prior price swing low.
- Entry (long): on the bar the bullish divergence is confirmed (the more
  recent, lower price swing low bar).
- Exit: close crosses back above its `exit_sma_window`-day SMA (mean
  reversion / trend re-confirmation), OR after `max_hold_days` (time-stop,
  consistent with other divergence strategies in this repo to bound risk
  from a pattern with no explicit stop in the source).
- Flat otherwise.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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


def _ad_line(df: pd.DataFrame) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    volume = df["volume"]
    rng = (high - low).replace(0.0, np.nan)
    clv = ((close - low) - (high - close)) / rng
    clv = clv.fillna(0.0)
    mfv = clv * volume
    return mfv.cumsum()


def generate_signals(
    price_df: pd.DataFrame,
    swing_window: int = 5,
    exit_sma_window: int = 20,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    ad = _ad_line(df)

    n = len(close)
    # Local swing low: close at bar i is the min over [i-swing_window, i+swing_window]
    is_swing_low = pd.Series(False, index=close.index)
    close_vals = close.values
    for i in range(swing_window, n - swing_window):
        window = close_vals[i - swing_window : i + swing_window + 1]
        if close_vals[i] == window.min():
            is_swing_low.iloc[i] = True

    swing_low_idxs = list(np.where(is_swing_low.values)[0])

    entry = pd.Series(False, index=close.index)
    prev_swing_i = None
    for i in swing_low_idxs:
        if prev_swing_i is not None:
            price_lower_low = close_vals[i] < close_vals[prev_swing_i]
            ad_higher_low = ad.iloc[i] > ad.iloc[prev_swing_i]
            if price_lower_low and ad_higher_low:
                entry.iloc[i] = True
        prev_swing_i = i

    sma = close.rolling(exit_sma_window).mean()
    exit_meanrev = close > sma

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or held >= max_hold_days:
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
