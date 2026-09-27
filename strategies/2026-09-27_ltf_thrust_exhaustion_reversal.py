"""Strategy: Thrust-Exhaustion-Reversal (3-bar momentum shift pattern),
daily-bar adaptation of LuxAlgo's intraday "LTF Momentum Projection" concept.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per LuxAlgo's "LTF Momentum Projection" indicator
(https://www.luxalgo.com/library/indicator/ltf-momentum-projection,
published Aug 4 2026, read this iteration via browser_exec -- web_search
DDGS backend returned empty/no results for this iteration's initial
keyword queries). Source's own disclosed "shift logic": "a strong thrust
candle with significant volume and body size, then a much smaller
exhaustion candle, then a close through the exhaustion candle's midpoint
in the opposite direction" marks a momentum shift (blue triangle = bullish
shift, red triangle = bearish). Operationalized here on daily bars, long
side only: (1) a bearish "thrust" bar with body >= thrust_body_atr_mult *
ATR and volume >= thrust_vol_mult * its own rolling average volume, (2) the
next bar is a small-bodied "exhaustion" bar with body <=
exhaustion_body_frac * the thrust bar's body, (3) a subsequent bar (within
confirm_window) closes above the exhaustion bar's own midpoint
((high+low)/2), confirming the reversal -- enter long on that close. This
is a genuinely distinct pattern from this repo's existing Crabel
Up/Down-Thrust (2026-09-20-146, a single-bar range-expansion breakout) and
Wyckoff Upthrust (2026-09-08-039, a false-breakout-above-resistance short
setup) -- this is a 3-bar sequential thrust->exhaustion->confirmed-reversal
structure that has never been tested in this repo.

Signal logic (long side only, daily-bar adaptation)
----------------------------------------------------
- Thrust bar (bearish): close < open, body = |close-open| >=
  thrust_body_atr_mult * ATR(atr_window), volume >= thrust_vol_mult *
  volume.rolling(vol_window).mean() (source's own "significant volume and
  body size").
- Exhaustion bar (next bar): body <= exhaustion_body_frac * thrust bar's
  body (source's "much smaller exhaustion candle").
- Confirmation: within confirm_window bars after the exhaustion bar,
  a bar's close crosses above the exhaustion bar's own midpoint
  ((high+low)/2) -- entry signal on that bar.
- Optional close>SMA(trend_window) uptrend gate (default False, since this
  is explicitly a REVERSAL pattern that source describes working against
  the prevailing short-term direction).
- Exit: max_hold_days time-stop, or close falling back below the thrust
  bar's own low (invalidation of the reversal).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    return df.sort_index()


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    thrust_body_atr_mult: float = 1.2,
    thrust_vol_mult: float = 1.3,
    exhaustion_body_frac: float = 0.4,
    confirm_window: int = 3,
    atr_window: int = 14,
    vol_window: int = 20,
    trend_window: int = 200,
    trend_filter: bool = False,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    openp = df["open"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=close.index)
    n = len(df)

    atr = _atr(df, atr_window)
    vol_avg = volume.rolling(vol_window).mean()
    sma_trend = close.rolling(trend_window).mean()
    uptrend = (close > sma_trend).fillna(False) if trend_filter else pd.Series(True, index=close.index)

    body = (close - openp).abs()
    is_bearish = close < openp

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    thrust_low = None

    i = max(atr_window, vol_window) + 1
    while i < n - 1:
        if in_position:
            held = i - entry_idx
            invalidated = thrust_low is not None and close.iloc[i] < thrust_low
            if invalidated or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                i += 1
                continue
            position.iloc[i] = 1
            i += 1
            continue

        a = atr.iloc[i]
        va = vol_avg.iloc[i]
        if pd.isna(a) or a == 0 or pd.isna(va) or va == 0:
            i += 1
            continue

        # Thrust bar check at i.
        if (
            bool(is_bearish.iloc[i])
            and body.iloc[i] >= thrust_body_atr_mult * a
            and volume.iloc[i] >= thrust_vol_mult * va
        ):
            thrust_body = body.iloc[i]
            t_low = low.iloc[i]
            # Exhaustion bar must be i+1.
            if i + 1 < n and body.iloc[i + 1] <= exhaustion_body_frac * thrust_body:
                exh_mid = (high.iloc[i + 1] + low.iloc[i + 1]) / 2.0
                found_entry = None
                for j in range(i + 2, min(i + 2 + confirm_window, n)):
                    if close.iloc[j] > exh_mid and bool(uptrend.iloc[j]):
                        found_entry = j
                        break
                if found_entry is not None:
                    in_position = True
                    entry_idx = found_entry
                    thrust_low = t_low
                    i = found_entry
                    position.iloc[i] = 1
                    i += 1
                    continue

        position.iloc[i] = 0
        i += 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
