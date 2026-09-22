"""Strategy: Wyckoff Phase C Test -- Spring + lower-volume retest entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-XXX):
Source: https://algobars.com/strategy-templates/wyckoff-complete/wyckoff-phase-c-test/
(accessed 2026-09-22, browser_exec after web_extract ddgs-backend refused
extraction). Distinct TWO-STAGE mechanic from this repo's prior single-stage
Wyckoff Spring entries (2026-09-09-105/106 single spring-probe-and-reclaim;
2026-09-16-181 single support-break-and-reclaim; 2026-09-10-006 SOS/LPS
breakout-continuation, opposite direction): Phase C requires (1) a genuine
Spring event (price pierces below a trading-range low and reverses), THEN
(2) a subsequent "test" bar that RETURNS to approximately the same Spring
low level, on volume NOTABLY LESS than the Spring bar's own volume ("supply
exhausted"), THEN (3) a bullish reversal candle confirms the test. Source's
own risk placement: stop below the ORIGINAL SPRING LOW (not the test low --
"give it room"), target at the top of the trading range (source states
"typically 3R+").

Signal logic (daily bars)
--------------------------
- Trading range detection: over a rolling `range_lookback`-day window,
  identify a consolidation range as periods where (rolling_high -
  rolling_low) / rolling_mid <= `range_width_pct` (same range-detection
  convention as this repo's existing Wyckoff Spring/Upthrust strategies).
- Range top/low = rolling max(high)/min(low) over that lookback window
  (evaluated at the bar just before the Spring, i.e. shifted to avoid
  lookahead into the Spring bar itself).
- Spring event at bar s: low_s < range_low_{s-1} * (1 - spring_penetration_pct)
  AND close_s > range_low_{s-1} (closes back inside the range -- the
  "briefly pierced and reversed" condition).
- Test event at a later bar t (within `test_window_days` of the Spring,
  t > s): low_t approximately revisits the Spring low
  (|low_t - low_s| / low_s <= test_proximity_pct) AND volume_t <=
  `test_volume_ratio` * volume_s (source's "notably less" volume
  requirement) AND close_t > open_t (source's "bullish reversal candle").
- Entry (long) at close of the test bar t.
- Exit: close reaches the range top (target, source's "typically 3R+"), OR
  close falls below the ORIGINAL spring low (stop, source's explicit "not
  the test low, give it room"), OR a `max_hold_days` time-stop.
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
    range_width_pct: float = 0.12,
    spring_penetration_pct: float = 0.01,
    test_window_days: int = 20,
    test_proximity_pct: float = 0.02,
    test_volume_ratio: float = 0.7,
    max_hold_days: int = 30,
) -> pd.Series:
    df = _prep(price_df)
    high, low, close, open_ = df["high"], df["low"], df["close"], df["open"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=df.index)

    roll_high = high.rolling(range_lookback).max()
    roll_low = low.rolling(range_lookback).min()
    roll_mid = (roll_high + roll_low) / 2.0
    range_width = (roll_high - roll_low) / roll_mid
    in_range_regime = (range_width <= range_width_pct).fillna(False)

    # Shift range boundaries by 1 to avoid the Spring bar itself contaminating
    # the range definition it's supposed to be piercing.
    range_low_prior = roll_low.shift(1)
    range_high_prior = roll_high.shift(1)
    in_range_prior = in_range_regime.shift(1).fillna(False)

    spring_event = (
        (low < range_low_prior * (1 - spring_penetration_pct))
        & (close > range_low_prior)
        & in_range_prior
    ).fillna(False)

    n = len(df)
    low_arr = low.to_numpy()
    close_arr = close.to_numpy()
    open_arr = open_.to_numpy()
    vol_arr = volume.to_numpy()
    spring_arr = spring_event.to_numpy()
    range_high_arr = range_high_prior.to_numpy()

    pos_arr = [0] * n
    in_pos = False
    hold_days = 0
    entry_stop = None
    entry_target = None

    pending_spring_idx = None
    pending_days_waited = 0

    for i in range(n):
        if in_pos:
            hold_days += 1
            hit_target = (entry_target is not None) and close_arr[i] >= entry_target
            hit_stop = close_arr[i] < entry_stop
            if hit_target or hit_stop or hold_days >= max_hold_days:
                in_pos = False
                pos_arr[i] = 0
                hold_days = 0
            else:
                pos_arr[i] = 1
            continue

        # Check pending spring for a valid test bar
        if pending_spring_idx is not None:
            pending_days_waited += 1
            s = pending_spring_idx
            spring_low = low_arr[s]
            spring_vol = vol_arr[s]
            is_test = (
                abs(low_arr[i] - spring_low) / spring_low <= test_proximity_pct
                and vol_arr[i] <= test_volume_ratio * spring_vol
                and close_arr[i] > open_arr[i]
            )
            if is_test:
                in_pos = True
                hold_days = 0
                entry_stop = spring_low
                target = range_high_arr[s]
                entry_target = target if not np.isnan(target) else close_arr[i] * 1.10
                pos_arr[i] = 1
                pending_spring_idx = None
                pending_days_waited = 0
                continue
            elif pending_days_waited >= test_window_days:
                pending_spring_idx = None
                pending_days_waited = 0

        if spring_arr[i] and pending_spring_idx is None:
            pending_spring_idx = i
            pending_days_waited = 0

        pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    range_lookback: int = 40,
    range_width_pct: float = 0.12,
    spring_penetration_pct: float = 0.01,
    test_window_days: int = 20,
    test_proximity_pct: float = 0.02,
    test_volume_ratio: float = 0.7,
    max_hold_days: int = 30,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        range_lookback=range_lookback,
        range_width_pct=range_width_pct,
        spring_penetration_pct=spring_penetration_pct,
        test_window_days=test_window_days,
        test_proximity_pct=test_proximity_pct,
        test_volume_ratio=test_volume_ratio,
        max_hold_days=max_hold_days,
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
