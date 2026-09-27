"""Strategy: Golden/Death Cross with volume confirmation, 200-SMA slope
filter, 2-day confirmation delay, and an ATR trailing stop.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-XXX):
Per a Google AI-overview synthesis (QuanTt/altFINS/TOS-Indicators sources,
read via browser_exec Google SERP fallback -- web_search DDGS returned no
results for this query), the classic 50/200-day SMA Golden Cross / Death
Cross whipsaws on ambiguous, low-conviction crossovers. The disclosed
composite rule adds FOUR independent confirmation layers, none of which
(in this exact combination) has been tested in this repo before:

  1. Volume filter: the crossover bar's volume must exceed 1.2x its own
     50-day average volume (vs this repo's prior volume-confirmed golden
     cross, 2026-09-17-141, which used a FROZEN post-cross breakout level
     + volume on the BREAKOUT bar, a different mechanic).
  2. Trend-slope filter: the 200-day SMA itself must have a flat-or-rising
     slope over the last 5 bars for a golden-cross long entry (SMA200_t >=
     SMA200_{t-5}) -- distinct from this repo's plain golden-cross entries,
     none of which gate on the SLOPE of the long SMA itself.
  3. Confirmation delay: require the crossover condition (50-SMA above
     200-SMA, volume, and slope all satisfied) to hold for 2 CONSECUTIVE
     closes before entering on the following bar (source's own "wait for
     2 consecutive daily closes past the crossover level" rule) -- distinct
     from every prior single-bar-trigger golden cross in this repo.
  4. ATR trailing stop: once long, an initial stop at 1.5x ATR below the
     crossover day's low, ratcheting upward thereafter (SuperTrend-style,
     never trailing back down) -- distinct from the plain SMA-crossover
     exit (death cross) used by most prior golden-cross entries; here the
     ATR stop can exit the position BEFORE a death cross forms.

Exit: close falls below the ratcheting ATR trailing stop, OR a death cross
occurs (50-SMA closes back below 200-SMA), whichever comes first.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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


def _atr(df: pd.DataFrame, atr_window: int) -> pd.Series:
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
    return tr.rolling(atr_window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 50,
    slow_window: int = 200,
    slope_lookback: int = 5,
    volume_avg_window: int = 50,
    volume_mult_required: float = 1.2,
    confirm_bars: int = 2,
    atr_window: int = 14,
    atr_stop_mult: float = 1.5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(0.0, index=close.index)

    sma_fast = close.rolling(fast_window).mean()
    sma_slow = close.rolling(slow_window).mean()
    slow_slope_ok = sma_slow >= sma_slow.shift(slope_lookback)

    vol_avg = volume.rolling(volume_avg_window).mean()
    vol_ok = volume >= (volume_mult_required * vol_avg)

    golden_cross_state = sma_fast > sma_slow
    entry_condition = golden_cross_state & slow_slope_ok & vol_ok

    # Confirmation: condition must hold for `confirm_bars` consecutive bars.
    confirmed = entry_condition.rolling(confirm_bars).sum() >= confirm_bars

    atr = _atr(df, atr_window)

    n = len(close)
    close_v = close.values
    low_v = low.values
    confirmed_v = confirmed.values
    golden_v = golden_cross_state.values
    atr_v = atr.values

    state = np.zeros(n, dtype=int)
    stop_level = np.full(n, np.nan)

    in_position = False
    for i in range(n):
        if np.isnan(atr_v[i]) or np.isnan(close_v[i]):
            state[i] = 0
            continue

        if not in_position:
            if confirmed_v[i]:
                in_position = True
                stop_level[i] = low_v[i] - atr_stop_mult * atr_v[i]
                state[i] = 1
            else:
                state[i] = 0
        else:
            prev_stop = stop_level[i - 1] if i > 0 and not np.isnan(stop_level[i - 1]) else (
                low_v[i] - atr_stop_mult * atr_v[i]
            )
            candidate_stop = close_v[i] - atr_stop_mult * atr_v[i]
            new_stop = max(prev_stop, candidate_stop)
            stop_level[i] = new_stop

            death_cross = not golden_v[i]
            stopped_out = close_v[i] < new_stop

            if death_cross or stopped_out:
                in_position = False
                state[i] = 0
            else:
                state[i] = 1

    signal = pd.Series(state, index=close.index).shift(1).fillna(0).astype(int)
    return signal


def generate_returns(
    price_df: pd.DataFrame,
    fast_window: int = 50,
    slow_window: int = 200,
    slope_lookback: int = 5,
    volume_avg_window: int = 50,
    volume_mult_required: float = 1.2,
    confirm_bars: int = 2,
    atr_window: int = 14,
    atr_stop_mult: float = 1.5,
) -> pd.Series:
    """Daily strategy returns, position-weighted, no transaction costs."""
    df = _prep(price_df)
    close = df["close"]
    positions = generate_signals(
        price_df,
        fast_window=fast_window,
        slow_window=slow_window,
        slope_lookback=slope_lookback,
        volume_avg_window=volume_avg_window,
        volume_mult_required=volume_mult_required,
        confirm_bars=confirm_bars,
        atr_window=atr_window,
        atr_stop_mult=atr_stop_mult,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = positions * daily_ret
    return strat_ret.fillna(0.0)
