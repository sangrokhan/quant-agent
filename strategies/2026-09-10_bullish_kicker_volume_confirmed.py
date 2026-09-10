"""Strategy: Bullish Kicker candlestick pattern, volume-spike confirmed.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per https://www.quantifiedstrategies.com/bullish-kicker-candlestick-pattern/:
the Bullish Kicker pattern is (1) a bearish candle, followed by (2) a candle
that gaps UP -- opens above the prior day's close -- and closes as a bullish
candle with the gap left completely unfilled (day2's low stays above day1's
close), signaling "a forceful shift in market momentum". The source
qualitatively suggests (without a numerically backtested threshold) that
confirming with a volume spike on the kicker bar strengthens the signal.
This implementation operationalizes that suggestion as a numeric filter:
require the kicker bar's volume to exceed vol_mult times its own trailing
average volume. First Kicker Pattern strategy in this repo -- distinct from
Bullish Engulfing (9 prior entries: requires body overlap/engulfment, no gap
requirement) since Kicker specifically requires an unfilled GAP between the
two candles.

Signal logic
------------
- Bearish candle at t-1: close[t-1] < open[t-1].
- Bullish Kicker at t: open[t] > close[t-1] (gap up open) AND close[t] >
  open[t] (bullish candle) AND low[t] > close[t-1] (gap left unfilled by
  the lower wick).
- Volume confirmation: volume[t] >= vol_mult * rolling_avg_volume(vol_window)[t]
  (source's own suggested enhancement, operationalized numerically).
- Entry (long): the confirmed Bullish Kicker bar, entered next bar's open
  approximated here as next-bar-close (this repo's return convention: signal
  at t triggers a position starting t+1 via the shift(1) in generate_returns).
- Exit: close crosses back below the entry-bar's low (source's own implicit
  "the gap should not get filled" invalidation level) OR a max_hold_days
  time-stop.

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
    vol_window: int = 20,
    vol_mult: float = 1.5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    open_ = df["open"]
    close = df["close"]
    low = df["low"]
    volume = df["volume"].astype(float)

    prev_close = close.shift(1)
    prev_open = open_.shift(1)

    bearish_prev = prev_close < prev_open
    gap_up_open = open_ > prev_close
    bullish_today = close > open_
    gap_unfilled = low > prev_close

    avg_volume = volume.rolling(vol_window).mean()
    volume_confirmed = volume >= vol_mult * avg_volume

    kicker_signal = (
        bearish_prev & gap_up_open & bullish_today & gap_unfilled & volume_confirmed
    ).fillna(False)

    invalidation_level = low.where(kicker_signal).ffill()

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_days = 0
    entry_vals = kicker_signal.values
    close_vals = close.values
    invalid_vals = invalidation_level.values

    for i in range(len(df)):
        if in_pos:
            hold_days += 1
            exit_now = (close_vals[i] < invalid_vals[i]) or (hold_days >= max_hold_days)
            if exit_now:
                in_pos = False
                hold_days = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_vals[i]:
                in_pos = True
                hold_days = 0
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    vol_window: int = 20,
    vol_mult: float = 1.5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    pos = generate_signals(
        price_df,
        vol_window=vol_window,
        vol_mult=vol_mult,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0)
    return strat_ret
