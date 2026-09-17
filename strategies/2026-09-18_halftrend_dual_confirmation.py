"""Strategy: HalfTrend (Alex Orekhov / TradingView "everget") dual-confirmation
trend flip, long-only ATR-channel breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-028):
Per mydailytake.com's fully-disclosed NinjaTrader 8 conversion writeup of
TradingView's "HalfTrend [everget]" indicator
(https://mydailytake.com/halftrend-everget-ninjatrader-8/, visited this
iteration via browser_exec after a Google SERP search -- web_search DDGS
backend unreliable this trigger), HalfTrend improves on SuperTrend-style
single-band-cross flips by requiring TWO independent conditions to agree
before flipping trend state:

- Smoothed extremes: SMA(High, amplitude) and SMA(Low, amplitude).
- Pivot levels: running max-of-low and running min-of-high, tracked since
  the last flip, over the `amplitude` window.
- Down-flip (uptrend -> downtrend): SMA(High) < running_max_low AND
  Close < prior bar's low, both true on the same bar.
- Up-flip (downtrend -> uptrend): SMA(Low) > running_min_high AND
  Close > prior bar's high, both true on the same bar.
- The active HalfTrend line sits at the pivot level of the most recent
  flip; ATR channels bracket it at (line +/- channel_deviation * ATR/2)
  for visualization (not used as an entry trigger here, though a wider
  variant could gate entries on channel width -- left for a follow-up).

This repo has zero prior HalfTrend entries. It differs fundamentally from
existing SuperTrend/PSAR/Chandelier-style single-condition ATR-band flips
already tested (dozens of entries) because BOTH the smoothed-MA condition
AND the raw-price-vs-prior-extreme condition must agree on the same bar --
the source's own stated advantage is fewer, higher-conviction flips than
SuperTrend with comparable settings.

Signal logic (long-only adaptation for daily equity/crypto bars)
------------------------------------------------------------------
- amplitude: SMA/pivot lookback window (source default 2).
- Long entry: trend state flips from down to up (per the up-flip condition
  above), entered next bar via the standard shift(1) in generate_returns.
- Exit: trend state flips from up to down (down-flip condition), or a
  max_hold_days time-stop.

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


def _halftrend_state(df: pd.DataFrame, amplitude: int) -> pd.Series:
    """Returns a boolean Series: True = uptrend, False = downtrend."""
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    close = df["close"].to_numpy(dtype=float)
    n = len(df)

    sma_high = df["high"].rolling(amplitude).mean().to_numpy(dtype=float)
    sma_low = df["low"].rolling(amplitude).mean().to_numpy(dtype=float)

    uptrend = np.empty(n, dtype=bool)
    # running pivot trackers, reset at each flip
    running_max_low = low[0] if n else np.nan
    running_min_high = high[0] if n else np.nan
    trend_up = True  # assume uptrend at series start

    for i in range(n):
        if i == 0:
            uptrend[i] = trend_up
            continue

        prior_low = low[i - 1]
        prior_high = high[i - 1]

        # Update running pivot trackers within the current trend state.
        if trend_up:
            running_max_low = max(running_max_low, low[i]) if not np.isnan(running_max_low) else low[i]
        else:
            running_min_high = min(running_min_high, high[i]) if not np.isnan(running_min_high) else high[i]

        sh, sl = sma_high[i], sma_low[i]
        flipped = False
        if trend_up and not np.isnan(sh):
            if sh < running_max_low and close[i] < prior_low:
                trend_up = False
                running_min_high = high[i]
                flipped = True
        elif (not trend_up) and not np.isnan(sl):
            if sl > running_min_high and close[i] > prior_high:
                trend_up = True
                running_max_low = low[i]
                flipped = True

        uptrend[i] = trend_up

    return pd.Series(uptrend, index=df.index)


def generate_signals(
    price_df: pd.DataFrame,
    amplitude: int = 2,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    uptrend = _halftrend_state(df, amplitude)
    flip_up = uptrend & (~uptrend.shift(1).fillna(uptrend.iloc[0] if len(uptrend) else True))
    flip_down = (~uptrend) & (uptrend.shift(1).fillna(uptrend.iloc[0] if len(uptrend) else True))

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_now = bool(flip_down.iloc[i]) if pd.notna(flip_down.iloc[i]) else False
            if exit_now or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            entry_now = bool(flip_up.iloc[i]) if pd.notna(flip_up.iloc[i]) else False
            if entry_now:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    amplitude: int = 2,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(df, amplitude=amplitude, max_hold_days=max_hold_days)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
