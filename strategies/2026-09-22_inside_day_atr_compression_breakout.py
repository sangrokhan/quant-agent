"""Strategy: Inside Day + 20-day-low ATR compression breakout (EMA50 trend).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-XXX):
Source: https://algobars.com/strategy-templates/volatility/inside-day-low-atr/
(accessed 2026-09-22, browser_exec after web_extract ddgs-backend refused
extraction). Template: an "inside day" (today's high < yesterday's high AND
today's low > yesterday's low) combined with ATR(14) sitting at a
`atr_lookback`-day LOW ("volatility compressed") is a "double compression"
setup ("a coiled spring"); trade the breakout of the inside day's range in
the direction of the EMA(50) trend for outsized moves. Distinct from this
repo's prior Inside Day entries (2026-09-04-090 EMA-trend-filtered breakout
with no ATR-compression gate; 2026-09-07-006/007 gap-down pullback,
same-bar-close entry, no breakout; 2026-09-08-069 Fakey false-breakout
reversal; 2026-09-22-014 StochRSI+Chaikin oscillator confirmation) via the
specific double-compression gate: inside day AND today's ATR(14) at (or near)
its own `atr_lookback`-day rolling minimum, not just a bare inside-day
pattern.

Signal logic (daily bars)
--------------------------
- Inside day at bar t: high_t < high_{t-1} AND low_t > low_{t-1}.
- ATR(14) compression: ATR(atr_window) at bar t is within
  `atr_compress_pct` of its own rolling `atr_lookback`-day minimum (i.e.
  ATR_t <= ATR_rolling_min_t * (1 + atr_compress_pct)) -- a soft version of
  the source's literal "at a 20-day low" to avoid over-narrow degenerate
  matching while keeping the compression-gate spirit.
- Trend filter: close_t > EMA(ema_window) (source's EMA 50, uptrend
  context).
- Entry (long), evaluated the day AFTER the inside day + compression + trend
  conditions all hold on day t: close_{t+1} (or a later day within
  `breakout_expiry_days`) breaks above the inside day's high (high_t).
- Exit: close reaches profit target = high_t + target_mult * (high_t -
  low_t) (source: "Target: 2x inside day range"), OR close drops below the
  inside day's low (stop, source: "Stop: below inside day's low"), OR
  `max_hold_days` time-stop, OR the setup's breakout_expiry_days elapses
  without a breakout (setup abandoned, no entry).
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
    atr_window: int = 14,
    atr_lookback: int = 20,
    atr_compress_pct: float = 0.10,
    ema_window: int = 50,
    target_mult: float = 2.0,
    breakout_expiry_days: int = 5,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    atr = _atr(df, atr_window)
    atr_roll_min = atr.rolling(atr_lookback).min()
    compressed = (atr <= atr_roll_min * (1.0 + atr_compress_pct)).fillna(False)

    inside_day = ((high < high.shift(1)) & (low > low.shift(1))).fillna(False)

    ema = close.ewm(span=ema_window, adjust=False).mean()
    uptrend = (close > ema).fillna(False)

    setup_bar = (inside_day & compressed & uptrend).fillna(False)

    n = len(df)
    setup_high = np.full(n, np.nan)
    setup_low = np.full(n, np.nan)
    setup_flag = setup_bar.to_numpy()
    high_arr = high.to_numpy()
    low_arr = low.to_numpy()
    close_arr = close.to_numpy()

    pos_arr = [0] * n
    in_pos = False
    hold_days = 0
    entry_high = None
    entry_low = None
    target_price = None
    pending_setup_idx = None  # index of the setup bar we're waiting to break out of
    pending_days_waited = 0

    for i in range(n):
        # Check for exit first if in position
        if in_pos:
            hold_days += 1
            hit_target = close_arr[i] >= target_price
            hit_stop = close_arr[i] < entry_low
            if hit_target or hit_stop or hold_days >= max_hold_days:
                in_pos = False
                pos_arr[i] = 0
                hold_days = 0
            else:
                pos_arr[i] = 1
            continue

        # Not in position: check for pending breakout setup
        if pending_setup_idx is not None:
            pending_days_waited += 1
            if close_arr[i] > setup_high[pending_setup_idx]:
                # breakout confirmed -> enter
                in_pos = True
                hold_days = 0
                entry_high = setup_high[pending_setup_idx]
                entry_low = setup_low[pending_setup_idx]
                target_price = entry_high + target_mult * (entry_high - entry_low)
                pos_arr[i] = 1
                pending_setup_idx = None
                pending_days_waited = 0
                continue
            elif pending_days_waited >= breakout_expiry_days:
                pending_setup_idx = None
                pending_days_waited = 0

        # New setup bar?
        if setup_flag[i] and pending_setup_idx is None:
            setup_high[i] = high_arr[i]
            setup_low[i] = low_arr[i]
            pending_setup_idx = i
            pending_days_waited = 0

        pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    atr_window: int = 14,
    atr_lookback: int = 20,
    atr_compress_pct: float = 0.10,
    ema_window: int = 50,
    target_mult: float = 2.0,
    breakout_expiry_days: int = 5,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        atr_window=atr_window,
        atr_lookback=atr_lookback,
        atr_compress_pct=atr_compress_pct,
        ema_window=ema_window,
        target_mult=target_mult,
        breakout_expiry_days=breakout_expiry_days,
        max_hold_days=max_hold_days,
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
