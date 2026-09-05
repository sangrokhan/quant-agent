"""Strategy: Dual EMA(9/21) crossover confirmed by Heikin-Ashi candle color,
long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-081):
Per a Facebook "Spider Software - Algo Trading & Technical Analysis
Platform" post (via Google search snippet): "Short Entry (Sell): Look for
the 9-period EMA to cross below the 21-period EMA, confirmed by red
Heikin-Ashi candles." By symmetry the long-side rule is: 9-period EMA
crosses above the 21-period EMA, confirmed by a green (bullish, HA_close >
HA_open) Heikin-Ashi candle. This is distinct from every prior Heikin Ashi
strategy in this repo: 2026-09-04-045 used a SINGLE EMA trend filter plus
counting N CONSECUTIVE same-color HA candles as the PRIMARY signal (no EMA
crossover at all); 2026-09-05-051 used HA color-streak counting as a
CONTRARIAN mean-reversion signal (opposite economic logic, no EMA at all).
Here the price EMA(9/21) crossover is the PRIMARY trend-following trigger,
and the Heikin-Ashi candle's color at that exact bar is a confirmation
FILTER (must already be bullish, not itself the signal) -- a genuinely
different construction from both prior entries.

Signal logic
------------
- Heikin-Ashi OHLC transform: HA_close = (O+H+L+C)/4; HA_open[0] =
  (O[0]+C[0])/2, HA_open[t] = (HA_open[t-1]+HA_close[t-1])/2.
- Fast EMA(fast_span) and slow EMA(slow_span) of the RAW close (not HA
  close, per the source's "price chart" EMA convention).
- Entry (long): fast EMA crosses above slow EMA AND HA_close > HA_open at
  that bar (green/bullish HA candle confirms the crossover).
- Exit: fast EMA crosses back below slow EMA, OR a max_hold_days
  time-stop.
- Flat otherwise.

Interface contract (RESEARCH_LOOP.md Step 5):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def _heikin_ashi(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    o = df["open"]
    h = df["high"]
    l = df["low"]
    c = df["close"]

    ha_close = (o + h + l + c) / 4.0
    ha_open = pd.Series(index=df.index, dtype=float)
    ha_open.iloc[0] = (o.iloc[0] + c.iloc[0]) / 2.0
    ha_close_vals = ha_close.to_numpy()
    ha_open_vals = ha_open.to_numpy().copy()
    for i in range(1, len(df)):
        ha_open_vals[i] = (ha_open_vals[i - 1] + ha_close_vals[i - 1]) / 2.0
    ha_open = pd.Series(ha_open_vals, index=df.index)
    return ha_open, ha_close


def generate_signals(
    price_df: pd.DataFrame,
    fast_span: int = 9,
    slow_span: int = 21,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ema_fast = close.ewm(span=fast_span, adjust=False).mean()
    ema_slow = close.ewm(span=slow_span, adjust=False).mean()

    ha_open, ha_close = _heikin_ashi(df)
    ha_bullish = ha_close > ha_open

    bull_cross = (ema_fast > ema_slow) & (ema_fast.shift(1) <= ema_slow.shift(1))
    bear_cross = (ema_fast < ema_slow) & (ema_fast.shift(1) >= ema_slow.shift(1))

    entry = bull_cross.fillna(False) & ha_bullish.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    entry_vals = entry.to_numpy()
    bear_vals = bear_cross.fillna(False).to_numpy()

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(bear_vals[i]) or held >= max_hold_days:
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
