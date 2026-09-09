"""Strategy: Wyckoff Spring (accumulation-range failed-breakdown reversal),
long-only, on daily bars.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per sdk-trading.com's Wyckoff Spring definition (Dennis York): "A Wyckoff
spring is a failed downside probe below the lower boundary of a trading
range. The move becomes meaningful only if price returns into the prior
range instead of accepting lower prices below support." Operationalized:
(1) a trading range is defined by the rolling N-day high/low over a
lookback window (range_window) prior to the probe bar, (2) the probe bar's
low dips below the range's lower boundary (range_low), (3) that same bar
(or within confirm_bars) closes back INSIDE the prior range (close >
range_low) -- the "failed breakdown" / return condition. This confirms a
Spring and triggers a long entry. Exit at a close above the range's upper
boundary (range_high, breakout resolves bullish, target achieved), a close
back below the probe bar's low (spring failed after all, structural stop),
or a max_hold_days time-stop.

This is the direct long-side mirror of this repo's already-tested Wyckoff
Upthrust strategy (2026-09-08-039, https://algobars.com/strategy-templates/
wyckoff-complete/wyckoff-upthrust/ -- "The Upthrust is the distribution
equivalent of the Spring"), but is a genuinely distinct, novel strategy in
this repo since no prior entry implements the accumulation-side Spring
pattern itself.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    range_window: int = 20,
    confirm_bars: int = 1,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]
    high = df["high"]

    # Trading range boundaries computed from the window PRIOR to the
    # current bar (shift(1)) so the probe bar itself doesn't distort its
    # own reference range.
    range_low = low.shift(1).rolling(range_window).min()
    range_high = high.shift(1).rolling(range_window).max()

    probe_below = low < range_low
    # Confirmation: within confirm_bars, close returns back inside the
    # range (close > range_low). confirm_bars=1 means the SAME bar's close
    # must already be back inside the range (classic same-bar spring).
    if confirm_bars <= 1:
        spring_confirmed = probe_below & (close > range_low)
    else:
        close_back_inside = close > range_low
        # confirmed if probe happened and, within the next confirm_bars
        # (inclusive of the probe bar), close gets back above range_low.
        confirmed_recent = close_back_inside.rolling(confirm_bars, min_periods=1).max().astype(bool)
        spring_confirmed = probe_below.shift(confirm_bars - 1).fillna(False).astype(bool) & confirmed_recent

    probe_low_value = low.where(probe_below).ffill()

    idx_list = close.index
    entry_arr = spring_confirmed.reindex(idx_list).fillna(False).to_numpy()
    close_arr = close.to_numpy()
    range_high_arr = range_high.to_numpy()
    probe_low_arr = probe_low_value.reindex(idx_list).to_numpy()

    pos_arr = [0] * len(idx_list)
    in_position = False
    entry_idx = -1
    stop_level = None

    for i in range(len(idx_list)):
        if not in_position:
            if entry_arr[i]:
                in_position = True
                entry_idx = i
                stop_level = probe_low_arr[i]
                pos_arr[i] = 1
        else:
            held = i - entry_idx
            hit_target = (range_high_arr[i] == range_high_arr[i]) and close_arr[i] > range_high_arr[i]
            hit_stop = (stop_level == stop_level) and close_arr[i] < stop_level
            if hit_target or hit_stop or held >= max_hold_days:
                in_position = False
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1

    return pd.Series(pos_arr, index=idx_list, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    range_window: int = 20,
    confirm_bars: int = 1,
    max_hold_days: int = 20,
) -> pd.Series:
    """Daily strategy returns (no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        range_window=range_window,
        confirm_bars=confirm_bars,
        max_hold_days=max_hold_days,
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_ret
