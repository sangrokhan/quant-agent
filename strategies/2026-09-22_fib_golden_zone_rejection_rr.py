"""Strategy: Fibonacci 61.8% "Golden Zone" pullback continuation w/ rejection
candle trigger, ATR stop, fixed 2:1 R:R target, EMA(50/200) trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-XXX):
Source: Google AI Overview synthesis (accessed 2026-09-22, corroborating
apptrading.ai / VT Markets / FX Replay content) plus
https://www.vtmarkets.com/discover/fibonacci-retracement-levels-a-practical-trading-guide/
for the level definitions. Distinct from prior KB entries 2026-09-03-022
(near-miss) and its direct rescue 2026-09-20-086 (also rejected): those
strategies used a *zone* entry (any close landing in the 50-78.6%
retracement band) with a swing-high-breakout exit. This iteration instead
implements the article's more specific 3-part rule that the prior attempts
did NOT test:
  1. **EMA(50/200) trend confluence filter** ("adding a 50 or 200 EMA
     filter increases the overall profit factor by reducing false
     breakouts") -- require EMA(50) > EMA(200) for longs (not just
     close > SMA(200) as the prior attempt used).
  2. **Rejection-candle trigger AT the 61.8% level specifically** (not a
     zone): entry only fires on the bar where the low pierces within
     `tol` of the 61.8% retracement level and the candle closes back above
     it with a lower wick (a "rejection" bar) -- not merely being inside a
     50-78.6% band on any bar.
  3. **Fixed R:R exit** ("optimal performance clusters around a fixed 2:1")
     via an ATR-based stop (source: "1 ATR beyond the 78.6% level") and a
     take-profit at `rr_multiple`x that stop distance, rather than the
     prior "exit on new swing high or break of swing low" exit mechanic.

Signal logic (daily bars, causal/no look-ahead)
------------------------------------------------
- Trend filter: EMA(ema_fast) > EMA(ema_slow) (default 50/200).
- Impulse leg: rolling `swing_lookback`-day high (swing_high) and the
  lowest low preceding it within the same window (swing_low).
- Golden level: golden = swing_high - 0.618 * (swing_high - swing_low).
- Rejection trigger (long): bar's low <= golden * (1 + tol) [wick pierced
  at/through 61.8%] AND bar's close > golden [closed back above it] AND
  trend filter holds.
- Stop-loss: 78.6% retracement level minus `atr_stop_mult` * ATR(atr_window)
  (approximating "beyond the 78.6% level, 1 ATR").
- Take-profit: entry_price + rr_multiple * (entry_price - stop_price).
- Exit: close <= stop_price (stop hit) OR close >= take_profit (target
  hit) OR `max_hold_days` elapsed (time-stop safety net not in source but
  needed to avoid indefinite holds when neither level is touched).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    ema_fast: int = 50,
    ema_slow: int = 200,
    swing_lookback: int = 30,
    tol: float = 0.005,
    atr_window: int = 14,
    atr_stop_mult: float = 1.0,
    rr_multiple: float = 2.0,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    ema_f = close.ewm(span=ema_fast, adjust=False).mean()
    ema_s = close.ewm(span=ema_slow, adjust=False).mean()
    trend_ok = ema_f > ema_s

    swing_high = high.rolling(swing_lookback).max()
    swing_low = low.rolling(swing_lookback).min()

    golden = swing_high - 0.618 * (swing_high - swing_low)
    deep = swing_high - 0.786 * (swing_high - swing_low)
    atr = _atr(df, atr_window)

    rejection = (low <= golden * (1 + tol)) & (close > golden) & trend_ok

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    entry_price = None
    stop_price = None
    tp_price = None
    hold_days = 0

    rejection_arr = rejection.fillna(False).to_numpy()
    close_arr = close.to_numpy()
    deep_arr = deep.to_numpy()
    atr_arr = atr.to_numpy()

    for i in range(len(close)):
        c = close_arr[i]
        if not in_pos:
            if rejection_arr[i] and not pd.isna(deep_arr[i]) and not pd.isna(atr_arr[i]):
                in_pos = True
                entry_price = c
                stop_price = deep_arr[i] - atr_stop_mult * atr_arr[i]
                risk = entry_price - stop_price
                tp_price = entry_price + rr_multiple * risk if risk > 0 else None
                hold_days = 0
                position.iloc[i] = 1
        else:
            hold_days += 1
            hit_stop = stop_price is not None and c <= stop_price
            hit_tp = tp_price is not None and c >= tp_price
            timed_out = hold_days >= max_hold_days
            if hit_stop or hit_tp or timed_out:
                in_pos = False
                position.iloc[i] = 0
                entry_price = stop_price = tp_price = None
            else:
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    ema_fast: int = 50,
    ema_slow: int = 200,
    swing_lookback: int = 30,
    tol: float = 0.005,
    atr_window: int = 14,
    atr_stop_mult: float = 1.0,
    rr_multiple: float = 2.0,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        ema_fast=ema_fast,
        ema_slow=ema_slow,
        swing_lookback=swing_lookback,
        tol=tol,
        atr_window=atr_window,
        atr_stop_mult=atr_stop_mult,
        rr_multiple=rr_multiple,
        max_hold_days=max_hold_days,
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
