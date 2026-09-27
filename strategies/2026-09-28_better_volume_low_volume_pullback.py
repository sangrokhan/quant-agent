"""Strategy: Better Volume Classifications "Low Volume test print" pullback
buy in an established uptrend, with a Climax-Down defensive exit.

Hypothesis (source: https://www.luxalgo.com/library/indicator/better-volume-classifications/,
read 2026-09-28 via browser_exec while browsing LuxAlgo's Volume Behavior
family for a candidate distinct from this repo's already-tested Better
Volume buy/sell-pressure apportionment, 2026-09-17-029/2026-09-18-132):

LuxAlgo's Better Volume Classifications benchmarks each bar's raw volume,
volume x range, and volume / range against ROLLING EXTREMES over a lookback
window (default 20) -- a fundamentally different construction from a fixed
volume-multiple threshold. Source's own trading guidance:
- "Low Volume: the window's quietest bar, the classic test print that
  supports continuation on a pullback."
- "Climax Up / Climax Down: extreme volume x range catches a final rush of
  aggressive buyers or sellers ... After an extended move it is an
  exhaustion alert."

This is distinct from every prior volume-climax strategy in this repo:
2026-09-06-157 (Volume Climax Reversal) and 2026-09-16-085 (Selling-Climax
Wyckoff) both use a fixed volume-multiple threshold (e.g. >=2.5-4x average)
on raw volume alone, not the rolling-extreme classification across THREE
series (volume, volume*range, volume/range) that LuxAlgo's indicator uses.
It's also distinct from the already-tested Better Volume buy/sell-pressure
apportionment (2026-09-17-029), which uses a completely different formula
(Value1/Value2 open-close-range-based buy/sell split) unrelated to this
rolling multi-series extreme-classification scheme.

Hypothesis: within an established SMA uptrend, a "Low Volume" test print
(today's volume is the LOWEST of the trailing `lookback` bars) occurring on
a down-close day marks a low-conviction pullback that sellers couldn't push
with real participation -- source's own framing: "supports continuation on
a pullback." This should mark a higher-quality dip-buy entry than a
generic pullback buy with no volume confirmation. Conversely, a "Climax
Down" print (today's volume x range is the HIGHEST of the trailing window,
on a down-close day) while already long signals a genuine capitulation/
exhaustion event that should trigger a defensive exit rather than holding
through it, since per source framing this typically marks the terminal
leg of a decline (i.e. exiting ahead of further downside continuation
risk, consistent with this repo's long-only defensive-exit-overlay pattern
for otherwise-bearish reversal signatures).

Signal logic (daily-bar mechanical proxy for source's rolling multi-series
classification):
- trend_ok = close > SMA(trend_window).
- rng = high - low.
- vol_range = volume * rng (the "climax" metric).
- is_low_volume = volume == rolling_min(volume, lookback) (today is the
  window's quietest bar).
- is_climax = vol_range == rolling_max(vol_range, lookback) (today is the
  window's most extreme effort bar).
- down_close = close < open.
- Entry: trend_ok AND is_low_volume AND down_close (a quiet, low-conviction
  pullback bar within an uptrend) AND not already in a position.
- Exit: trend_ok breaks (close < SMA(trend_window)), OR a Climax-Down print
  (is_climax AND down_close) while long, OR a max_hold_days time-stop --
  whichever comes first.

Interface contract (see validation/validators.py and validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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
    trend_window: int = 50,
    lookback: int = 20,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    sma = close.rolling(trend_window).mean()
    trend_ok = close > sma

    rng = high - low
    vol_range = volume * rng

    rolling_min_vol = volume.rolling(lookback).min()
    rolling_max_vr = vol_range.rolling(lookback).max()

    is_low_volume = volume <= rolling_min_vol
    is_climax = vol_range >= rolling_max_vr
    down_close = close < open_

    entry_signal = trend_ok & is_low_volume & down_close
    climax_down = is_climax & down_close

    n = len(df)
    trend_ok_arr = trend_ok.to_numpy()
    entry_signal_arr = entry_signal.fillna(False).to_numpy()
    climax_down_arr = climax_down.fillna(False).to_numpy()

    pos = pd.Series(0.0, index=df.index)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_now = (
                not bool(trend_ok_arr[i])
                or bool(climax_down_arr[i])
                or hold_count >= max_hold_days
            )
            if exit_now:
                in_pos = False
                hold_count = 0
            else:
                pos.iloc[i] = 1.0
        if not in_pos and bool(entry_signal_arr[i]):
            in_pos = True
            hold_count = 0
            pos.iloc[i] = 1.0

    return pos


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    lookback: int = 20,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return the daily strategy return series (no transaction costs)."""
    df = _prep(price_df)
    pos = generate_signals(
        df,
        trend_window=trend_window,
        lookback=lookback,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0.0)
    return strat_ret
