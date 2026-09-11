"""Strategy: PMax (Profit Maximizer, KivancOzbilgic 2020) -- SuperTrend-style
ATR trailing stop applied to a Moving Average (not raw close), with an
MA-crosses-PMax entry/exit rule.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
PMax combines the ATR-band trailing-stop mechanism of SuperTrend with
Anil Ozeksi's MOST (Moving Stop Loss) idea of applying that trailing stop
to a smoothed MOVING AVERAGE of price rather than to raw close -- intended
to reduce whipsaws in sideways markets relative to either ancestor alone.
Per https://kr.tradingview.com/script/sU9molfV/ (creator KivancOzbilgic's
own TradingView page, visited via browser_exec/google.com fallback --
web_search DDGS backend TLS/connection errors on this iteration's initial
query): "We are under the effect of the uptrend in cases where the Moving
Average is above PMax; conversely under the influence of a downward
trend, when the Moving Average is below PMax... BUY when Moving Average
crosses above PMax, SELL when Moving Average crosses under PMax."

Construction: MA = EMA(close, ma_length); ATR = True-Range EMA(atr_period);
trailing-stop bands = MA +/- (atr_multiplier * ATR), ratcheted in the
favorable direction only (identical SuperTrend-style flip logic, but
applied to the smoothed MA series instead of close). Long entry when MA
crosses above the PMax trailing-stop line; exit (flat) when MA crosses
back below it, or a max_hold_days time-stop.

Distinct from this repo's 23+ prior SuperTrend variants -- all of those
apply the ATR trailing-stop to raw close/high/low directly; PMax's
defining innovation (per source) is applying the identical mechanism to
a pre-smoothed MOVING AVERAGE, which is a genuinely different signal
(fewer false flips in chop, per source's own stated design goal). First
PMax / MOST-hybrid strategy in this repo.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)


def _compute_pmax(
    ma: pd.Series, atr: pd.Series, atr_multiplier: float
) -> pd.Series:
    """SuperTrend-style ratcheted trailing stop applied to `ma` (not close)."""
    ma_vals = ma.values
    atr_vals = atr.values
    n = len(ma_vals)

    band = atr_vals * atr_multiplier
    long_stop = ma_vals - band
    short_stop = ma_vals + band

    pmax = np.empty(n)
    direction = np.empty(n, dtype=int)
    pmax[0] = long_stop[0] if not np.isnan(long_stop[0]) else ma_vals[0]
    direction[0] = 1
    for i in range(1, n):
        if np.isnan(ma_vals[i]) or np.isnan(atr_vals[i]):
            pmax[i] = pmax[i - 1]
            direction[i] = direction[i - 1]
            continue
        if direction[i - 1] == 1:
            new_long_stop = max(long_stop[i], pmax[i - 1]) if ma_vals[i] > pmax[i - 1] else long_stop[i]
            if ma_vals[i] < new_long_stop:
                direction[i] = -1
                pmax[i] = short_stop[i]
            else:
                direction[i] = 1
                pmax[i] = new_long_stop
        else:
            new_short_stop = min(short_stop[i], pmax[i - 1]) if ma_vals[i] < pmax[i - 1] else short_stop[i]
            if ma_vals[i] > new_short_stop:
                direction[i] = 1
                pmax[i] = long_stop[i]
            else:
                direction[i] = -1
                pmax[i] = new_short_stop

    return pd.Series(pmax, index=ma.index)


def generate_signals(
    price_df: pd.DataFrame,
    ma_length: int = 10,
    atr_period: int = 10,
    atr_multiplier: float = 3.0,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    ma = close.ewm(span=ma_length, adjust=False).mean()
    tr = _true_range(high, low, close)
    atr = tr.ewm(span=atr_period, adjust=False).mean()

    pmax = _compute_pmax(ma, atr, atr_multiplier)

    above = ma > pmax
    prev_above = above.shift(1)
    cross_up = above & ~prev_above.fillna(False)
    cross_down = ~above & prev_above.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(cross_down.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]):
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
