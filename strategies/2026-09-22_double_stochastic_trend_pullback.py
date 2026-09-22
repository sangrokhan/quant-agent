"""Strategy: Double Stochastic trend-pullback (macro/micro), long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-XXX):
Source: Google AI Overview (accessed 2026-09-22, corroborated by
easytradeweb.com's "Double Stochastic Strategy: Slow and Fast Forex
Settings" and UKspreadbetting/AlgoTrade Pro YouTube content). Distinct from
prior KB entry 2026-09-09-070 (Double Stochastic AGREEMENT oversold-bounce
-- both fast AND slow stochastics simultaneously oversold trigger a
mean-reversion bounce trade), this iteration implements a TREND-FOLLOWING
PULLBACK mechanic instead: the slow stochastic (21,3,3) identifies the
macro trend state (above 50 = bullish regime), while the FAST stochastic
(5,1,1) times entries on pullbacks WITHIN that established trend (crossing
UP from oversold <20, not simultaneous oversold agreement), confirmed by
price being above a 20-period EMA trend filter. Exit uses a fixed
risk-multiple ATR stop/target (1.5x ATR stop, 2.0x ATR target) rather than
2026-09-09-070's presumed oscillator-based exit.

Signal logic (daily bars, causal/no look-ahead)
------------------------------------------------
- Slow %K (slow_k_window, slow_smooth, slow_d_smooth) -- macro trend state:
  bullish regime when slow %K > 50.
- Fast %K (fast_k_window, fast_smooth, fast_d_smooth) -- pullback timing:
  entry trigger when fast %K crosses up through `oversold_thresh` (from
  below to at/above) while still below `neutral_thresh`.
- EMA(ema_window) trend confirmation: close > EMA.
- Entry (long): slow %K > 50 AND fast %K crosses up through oversold_thresh
  AND close > EMA(ema_window).
- Exit: close <= stop_price (entry - atr_stop_mult*ATR) OR close >=
  tp_price (entry + atr_tp_mult*ATR) OR `max_hold_days` elapsed.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _stochastic(df: pd.DataFrame, k_window: int, k_smooth: int, d_smooth: int):
    high, low, close = df["high"], df["low"], df["close"]
    lowest_low = low.rolling(k_window).min()
    highest_high = high.rolling(k_window).max()
    raw_k = 100 * (close - lowest_low) / (highest_high - lowest_low)
    k = raw_k.rolling(k_smooth).mean()
    d = k.rolling(d_smooth).mean()
    return k, d


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
    slow_k_window: int = 21,
    slow_smooth: int = 3,
    fast_k_window: int = 5,
    fast_smooth: int = 1,
    ema_window: int = 20,
    oversold_thresh: float = 20.0,
    atr_window: int = 14,
    atr_stop_mult: float = 1.5,
    atr_tp_mult: float = 2.0,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    slow_k, _ = _stochastic(df, slow_k_window, slow_smooth, slow_smooth)
    fast_k, _ = _stochastic(df, fast_k_window, fast_smooth, fast_smooth)
    ema = close.ewm(span=ema_window, adjust=False).mean()
    atr = _atr(df, atr_window)

    macro_bullish = slow_k > 50
    fast_cross_up = (fast_k >= oversold_thresh) & (fast_k.shift(1) < oversold_thresh)
    trend_ok = close > ema

    entry = macro_bullish & fast_cross_up & trend_ok

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    entry_price = None
    stop_price = None
    tp_price = None
    hold_days = 0

    entry_arr = entry.fillna(False).to_numpy()
    close_arr = close.to_numpy()
    atr_arr = atr.to_numpy()

    for i in range(len(close)):
        c = close_arr[i]
        if not in_pos:
            if entry_arr[i] and not pd.isna(atr_arr[i]):
                in_pos = True
                entry_price = c
                stop_price = entry_price - atr_stop_mult * atr_arr[i]
                tp_price = entry_price + atr_tp_mult * atr_arr[i]
                hold_days = 0
                position.iloc[i] = 1
        else:
            hold_days += 1
            hit_stop = c <= stop_price
            hit_tp = c >= tp_price
            timed_out = hold_days >= max_hold_days
            if hit_stop or hit_tp or timed_out:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    slow_k_window: int = 21,
    slow_smooth: int = 3,
    fast_k_window: int = 5,
    fast_smooth: int = 1,
    ema_window: int = 20,
    oversold_thresh: float = 20.0,
    atr_window: int = 14,
    atr_stop_mult: float = 1.5,
    atr_tp_mult: float = 2.0,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        slow_k_window=slow_k_window,
        slow_smooth=slow_smooth,
        fast_k_window=fast_k_window,
        fast_smooth=fast_smooth,
        ema_window=ema_window,
        oversold_thresh=oversold_thresh,
        atr_window=atr_window,
        atr_stop_mult=atr_stop_mult,
        atr_tp_mult=atr_tp_mult,
        max_hold_days=max_hold_days,
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
