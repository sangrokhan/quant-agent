"""Strategy: Bullish Outside Bar reversal (full-range engulf + close-position + volume filter).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-122):
Per https://journalplus.co/patterns/outside-bar-pattern/, a bullish Outside
Bar occurs when today's high/low FULLY engulf yesterday's high/low
(including wicks -- stricter than a body-only engulfing candle) AND
today's close falls in the upper 40% of today's own high-low range
(confirming buyers decisively won the session), optionally confirmed by
volume >= 1.5x the 20-day average (institutional participation). The
source states this "stricter test than the popular engulfing candlestick"
is "more reliable for that reason." Long entry at the close of a
qualifying outside bar; stop below the outside bar's OWN low (not the
engulfed prior candle's low, since that level was already breached); target
= the outside bar's own high-low range projected up from the close
(measured move), or a max-holding-period time-stop if neither the stop nor
target is hit first. First Outside Bar (full-range engulf) strategy in this
repo -- distinct from the already-tested Bullish Engulfing (body-only
engulf, no wick requirement, no close-position filter) and Bullish Kicker
(requires a non-overlapping gap, no engulf requirement).

Signal logic
------------
- Outside bar: today's high > yesterday's high AND today's low < yesterday's low.
- Bullish confirmation: (close - low) / (high - low) >= close_position_pct
  (default 0.60, i.e. upper 40% of the day's range).
- Optional volume filter: today's volume >= volume_mult * 20-day average volume.
- Entry: long at the close of a qualifying bullish outside bar.
- Exit: close >= entry_price + range_multiple * (bar's own high-low range)
  [measured-move target], OR close <= bar's own low [stop hit], OR
  max_hold_days elapses.
- Flat otherwise, long-only, one position at a time.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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
    close_position_pct: float = 0.60,
    volume_mult: float = 1.5,
    vol_window: int = 20,
    range_multiple: float = 1.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close, high, low, volume = df["close"], df["high"], df["low"], df["volume"]

    prev_high = high.shift(1)
    prev_low = low.shift(1)
    is_outside_bar = (high > prev_high) & (low < prev_low)

    bar_range = (high - low).replace(0, pd.NA)
    close_position = (close - low) / bar_range
    bullish_close = close_position >= close_position_pct

    avg_vol = volume.rolling(vol_window).mean().shift(1)
    volume_ok = volume >= (volume_mult * avg_vol)

    entry = is_outside_bar & bullish_close.fillna(False) & volume_ok.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_price = None
    target_price = None
    stop_price = None
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            hit_stop = close.iloc[i] <= stop_price
            hit_target = close.iloc[i] >= target_price
            if hit_stop or hit_target or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                entry_price = None
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                entry_price = close.iloc[i]
                rng = bar_range.iloc[i]
                target_price = entry_price + range_multiple * rng
                stop_price = low.iloc[i]
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
