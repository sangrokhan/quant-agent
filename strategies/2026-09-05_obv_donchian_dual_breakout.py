"""Strategy: Donchian price breakout confirmed by a simultaneous OBV breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-060):
Per TrendSpider's "On-Balance Volume Trading Strategies" article (OBV
Breakout Strategy section): a price breakout through a key resistance level
is more likely to be genuine (continuation) rather than a false breakout
when OBV is *simultaneously* breaking through its own analogous rolling
high, since that confirms the breakout is backed by real buying volume
pressure, not just a low-volume price spike. This is a distinct construction
from prior OBV strategies in this repo: 2026-09-04-027 used OBV-vs-its-own-EMA
crossover as a trend filter (no breakout, no rolling-high comparison);
2026-09-04-088 used OBV divergence (price makes new low, OBV doesn't) as a
reversal setup; 2026-09-04-166 used a pure price-breakout gated by a
relative-volume (RVOL) spike (no OBV, no dual-breakout structure). Here BOTH
price and OBV must independently break their own N-day rolling highs on the
same bar -- a dual-series breakout-confirmation rule that hasn't been tried
in this repo.

Signal logic
------------
- entry_window-day rolling high of close (excluding current bar) defines the
  price breakout level; entry_window-day rolling high of OBV (excluding
  current bar) defines the OBV breakout level.
- Long entry: close breaks above its own entry_window-day rolling high AND
  OBV breaks above its own entry_window-day rolling high on the same bar
  (dual confirmation -- price alone or OBV alone is not enough).
- Exit: close breaks below its own exit_window-day rolling low (trailing
  stop/trend exhaustion), OR a max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
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


def _obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff().fillna(0.0))
    return (direction * volume.fillna(0.0)).cumsum()


def generate_signals(
    price_df: pd.DataFrame,
    entry_window: int = 20,
    exit_window: int = 10,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    obv = _obv(close, volume)

    price_prior_high = close.shift(1).rolling(entry_window).max()
    obv_prior_high = obv.shift(1).rolling(entry_window).max()
    price_prior_low = close.shift(1).rolling(exit_window).min()

    entry = (close > price_prior_high) & (obv > obv_prior_high)
    exit_stop = close < price_prior_low

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_vals = entry.to_numpy()
    exit_vals = exit_stop.to_numpy()
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_vals[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_vals[i]):
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
