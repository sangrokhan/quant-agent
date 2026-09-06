"""Strategy: Fractal Chaos Bands (Bill Williams-style fractal envelope) breakout
with EMA trend confirmation, long-only.

Hypothesis (see knowledge_base id 2026-09-06-145):
Per Google AI-overview synthesis (LightningChart/GeekOnDaily/QuantifiedStrategies,
confirmed by multiple sources): Fractal Chaos Bands are a technical indicator
that plots a band above and below price based on 5-bar William fractals --
upper band = highest high of the last N confirmed UP fractals (a swing high
that has 2 lower highs on each side), lower band = lowest low of the last N
confirmed DOWN fractals. Google AI-overview's disclosed mechanical rule:
"Enter a buy trade when the price crosses and closes above the upper fractal
chaos band, ideally confirmed by a simultaneous close above a trend filter
like the 20-period EMA... Close the active position when a new opposing
fractal forms or when the price crosses back over the sloping trend
indicator or opposite band."

First Fractal Chaos Bands strategy in this repo (prior search attempts
(2026-09-05, search snippet id in visited_pages) found the topic but never
disclosed/tested a concrete numeric rule -- this Google AI-overview pass
finally surfaced one).

Signal logic
------------
- Fractal high: bar i is a confirmed up-fractal if high[i] is the max of
  high[i-2:i+3] (standard 5-bar William fractal, confirmed 2 bars later).
- Fractal low: bar i is a confirmed down-fractal if low[i] is the min of
  low[i-2:i+3].
- Upper band: running value of the most recent confirmed up-fractal's high
  (forward-filled until a new one appears).
- Lower band: running value of the most recent confirmed down-fractal's low
  (forward-filled).
- Trend filter: close > EMA(ema_window) (default 20, per source).
- Entry (long): close crosses above the upper band AND close > EMA(ema_window).
- Exit: a new down-fractal forms (opposing fractal), OR close crosses back
  below the EMA trend filter, OR close crosses below the lower band, OR a
  max_hold_days time-stop.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _fractals(high: pd.Series, low: pd.Series):
    n = len(high)
    up_fractal = np.zeros(n, dtype=bool)
    down_fractal = np.zeros(n, dtype=bool)
    h = high.values
    lo = low.values
    for i in range(2, n - 2):
        window_h = h[i - 2 : i + 3]
        if h[i] == window_h.max() and np.argmax(window_h) == 2:
            up_fractal[i] = True
        window_l = lo[i - 2 : i + 3]
        if lo[i] == window_l.min() and np.argmin(window_l) == 2:
            down_fractal[i] = True
    return pd.Series(up_fractal, index=high.index), pd.Series(down_fractal, index=high.index)


def generate_signals(
    price_df: pd.DataFrame,
    ema_window: int = 20,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]
    n = len(close)

    up_fractal, down_fractal = _fractals(high, low)
    # fractal confirmation happens 2 bars after formation (right side of the pattern)
    up_fractal_confirmed = up_fractal.shift(2).fillna(False).astype(bool)
    down_fractal_confirmed = down_fractal.shift(2).fillna(False).astype(bool)

    upper_band_raw = high.where(up_fractal_confirmed)
    lower_band_raw = low.where(down_fractal_confirmed)
    upper_band = upper_band_raw.ffill()
    lower_band = lower_band_raw.ffill()

    ema = close.ewm(span=ema_window, min_periods=ema_window, adjust=False).mean()
    trend_up = close > ema

    breakout = (close > upper_band) & (~(close.shift(1) > upper_band.shift(1)).fillna(False))
    entry = breakout.fillna(False) & trend_up.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(n):
        if in_position:
            held = i - entry_idx
            new_down_fractal = bool(down_fractal_confirmed.iloc[i])
            trend_break = not bool(trend_up.iloc[i])
            below_lower = (not np.isnan(lower_band.iloc[i])) and (close.iloc[i] < lower_band.iloc[i])
            if new_down_fractal or trend_break or below_lower or held >= max_hold_days:
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
