"""Strategy: 20/50 EMA crossover confirmed by RSI(14) > 50 midline.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-165):
A classic dual-EMA trend crossover (fast EMA(20) flipping above slow
EMA(50)) is a higher-conviction long entry when confirmed by RSI(14)
staying above its 50 midline (broad bullish momentum regime, not itself
overbought/oversold) at the crossover bar -- the RSI filter is meant to
avoid taking EMA crossovers during momentum-negative/choppy conditions.
Per a widely-circulated "Uptrend trading strategy using EMA and RSI
confirmation" rule (Entry: 20 EMA crosses above 50 EMA AND RSI(14) stays
above 50). Exit when the EMA crossover reverses (fast crosses back below
slow) OR RSI drops back below 50, OR a max_hold_days time-stop backstop.
Distinct from every prior dual-EMA-family crossover strategy in this repo
(plain EMA, ZLEMA 2026-09-04-066, DEMA 2026-09-04-079, TEMA 2026-09-04-068/
-070) since none of those combined an RSI-midline momentum confirmation
gate with the EMA cross itself.

Signal logic
------------
- Fast EMA(fast_span), Slow EMA(slow_span) of close.
- RSI(rsi_window) via Wilder smoothing.
- Entry (long): fast EMA crosses above slow EMA AND RSI > rsi_midline at
  that bar.
- Exit: fast EMA crosses below slow EMA, OR RSI crosses below rsi_midline,
  OR max_hold_days elapses since entry.
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


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    fast_span: int = 20,
    slow_span: int = 50,
    rsi_window: int = 14,
    rsi_midline: float = 50.0,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    fast_ema = close.ewm(span=fast_span, adjust=False).mean()
    slow_ema = close.ewm(span=slow_span, adjust=False).mean()
    rsi = _rsi(close, rsi_window)

    cross_up = (fast_ema > slow_ema) & (fast_ema.shift(1) <= slow_ema.shift(1))
    cross_down = (fast_ema < slow_ema) & (fast_ema.shift(1) >= slow_ema.shift(1))
    rsi_below_mid = rsi < rsi_midline

    entry_raw = cross_up & (rsi > rsi_midline)
    exit_raw = cross_down | rsi_below_mid

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
    fast_span: int = 20,
    slow_span: int = 50,
    rsi_window: int = 14,
    rsi_midline: float = 50.0,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        fast_span=fast_span,
        slow_span=slow_span,
        rsi_window=rsi_window,
        rsi_midline=rsi_midline,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
