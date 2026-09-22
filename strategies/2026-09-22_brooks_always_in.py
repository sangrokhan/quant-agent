"""Strategy: Al Brooks "Always-In" trend-bar + follow-through, EMA20-gated
stop-and-reverse.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-XXX):
Source: https://algobars.com/strategy-templates/al-brooks/brooks-always-in/
(accessed 2026-09-22, browser_exec after web_extract ddgs-backend refused
extraction). Al Brooks' "always-in" concept: the market is always either
always-in-long or always-in-short; flip your position when the always-in
direction flips. Source's explicit numeric rule:
  - Always-in-LONG trigger: a strong bullish trend bar closing on (or very
    near) its high, followed by a bullish follow-through bar, with price
    above the EMA(20).
  - Always-in-SHORT trigger (reversal): a strong bearish trend bar closing
    on (or very near) its low, followed by bearish follow-through,
    confirmed below the EMA(20).
  - No flat state -- the market is ALWAYS either always-in-long or
    always-in-short; you hold the current side until a reversal trigger.

This repo has no prior direct implementation of this specific
trend-bar+follow-through+EMA always-in mechanic (existing "always_in"-tagged
entries in the KB are all different constructions: Donchian stop-and-reverse,
ATR-ratchet SAR, TTF hysteresis-band, LBR 3/10 oscillator, COG
signal-line-cross -- none use Brooks' explicit "trend bar closing on its
extreme + follow-through bar + EMA20 side confirmation" trigger).

Signal logic (daily bars)
--------------------------
- Strong bullish trend bar at bar t: (close_t - open_t) is positive and in
  the top `trend_bar_pctile` percentile of the trailing `range_lookback`-day
  |close-open| distribution (a "strong" bar), AND close_t is within
  `close_near_extreme_pct` of high_t (closes "on its high").
- Bullish follow-through at bar t+1: close_{t+1} > close_t (continues in
  the same direction).
- Always-in-LONG trigger confirmed at bar t+1 if: strong bullish trend bar
  at t, bullish follow-through at t+1, AND close_{t+1} > EMA(ema_window)
  at t+1.
- Symmetric always-in-SHORT trigger (strong bearish trend bar closing near
  its low, bearish follow-through, close below EMA).
- Position: {-1, 0, +1} but structurally always-in once a first trigger has
  fired (no flat state after the first entry) -- flips instantly on the
  opposite trigger, held otherwise. Before the first trigger fires, flat.
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


def generate_signals(
    price_df: pd.DataFrame,
    range_lookback: int = 40,
    trend_bar_pctile: float = 0.75,
    close_near_extreme_pct: float = 0.20,
    ema_window: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    high, low, close, open_ = df["high"], df["low"], df["close"], df["open"]

    body = (close - open_).abs()
    body_threshold = body.rolling(range_lookback).quantile(trend_bar_pctile)

    bar_range = (high - low).replace(0, np.nan)
    close_pos_in_range = (close - low) / bar_range  # 0=low, 1=high

    strong_bull_bar = (
        (close > open_)
        & (body >= body_threshold)
        & (close_pos_in_range >= (1 - close_near_extreme_pct))
    ).fillna(False)

    strong_bear_bar = (
        (close < open_)
        & (body >= body_threshold)
        & (close_pos_in_range <= close_near_extreme_pct)
    ).fillna(False)

    ema = close.ewm(span=ema_window, adjust=False).mean()

    n = len(df)
    close_arr = close.to_numpy()
    ema_arr = ema.to_numpy()
    strong_bull_arr = strong_bull_bar.to_numpy()
    strong_bear_arr = strong_bear_bar.to_numpy()

    pos_arr = [0] * n
    current_side = 0  # 0 = not yet in a side, +1 = always-in-long, -1 = always-in-short

    for i in range(1, n):
        prev_strong_bull = strong_bull_arr[i - 1]
        prev_strong_bear = strong_bear_arr[i - 1]

        bullish_follow_through = close_arr[i] > close_arr[i - 1]
        bearish_follow_through = close_arr[i] < close_arr[i - 1]

        long_trigger = (
            prev_strong_bull and bullish_follow_through and close_arr[i] > ema_arr[i]
        )
        short_trigger = (
            prev_strong_bear and bearish_follow_through and close_arr[i] < ema_arr[i]
        )

        if long_trigger:
            current_side = 1
        elif short_trigger:
            current_side = -1
        # else: hold current_side (always-in, no flat state once established)

        pos_arr[i] = current_side

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    range_lookback: int = 40,
    trend_bar_pctile: float = 0.75,
    close_near_extreme_pct: float = 0.20,
    ema_window: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        range_lookback=range_lookback,
        trend_bar_pctile=trend_bar_pctile,
        close_near_extreme_pct=close_near_extreme_pct,
        ema_window=ema_window,
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
