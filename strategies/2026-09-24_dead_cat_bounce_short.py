"""Strategy: Dead Cat Bounce short-the-fade, daily bars.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-XXX):
Per Google SERP snippets of https://www.dxpa.in (institutional analytics
strategy page, full page 404s but SERP snippet discloses exact numeric
rule) and https://www.thinkmarkets.com (SERP snippet, full article 404s):
"The pattern starts with a sharp decline, usually 10 to 20% over 1 to 3
days, on heavy volume. The stock then bounces 3 to 5% on lighter volume"
before resuming the downtrend (ThinkMarkets: "shallow retracement of 23.6%
to 50%... on falling volume, and a rejection at resistance, then enter
short"). This repo has zero prior "dead cat bounce" entries -- distinct
from other reversal/continuation patterns already tested (Island
Reversal, Exhaustion Gap, Three Outside Down) since this specifically
requires a SHARP MULTI-DAY DECLINE (>= decline_pct over decline_window
days) followed by a SHALLOW BOUNCE (retracing only a fraction of the
decline, on lighter volume than the decline) before shorting the
resumption of the downtrend -- a decline-then-fade-then-continue sequence,
not a single-bar or simple-crossover trigger.

Signal logic
------------
- Decline: close fell by at least `decline_pct` (e.g. 0.10) over the prior
  `decline_window` trading days (e.g. 3), with average volume over that
  window >= `decline_vol_ratio` x its own 20-day average (heavy volume).
- Bounce: after the decline, price bounces (rises) but the bounce's
  cumulative gain stays below `bounce_cap_pct` (e.g. 0.05) of the decline
  low, AND the bounce day's volume is below its own 20-day average
  (lighter volume) -- confirms the bounce lacks conviction.
- Entry (short, expressed as -1 position): once both decline+weak-bounce
  conditions are confirmed, short at the bounce's local high.
- Exit: close makes a new low below the decline's low (downtrend resumed,
  take profit), OR close breaks back above the bounce high by more than a
  small buffer (thesis invalidated, stop out), OR after max_hold_days.
- Flat otherwise. NOTE: this strategy is short-only (position in {-1, 0}),
  unlike most strategies in this repo which are long-only {0, 1} -- the
  grid/validator machinery treats returns as position * daily_ret either
  way so this works unmodified with the standard interface.

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
    decline_window: int = 3,
    decline_pct: float = 0.04,
    decline_vol_ratio: float = 1.05,
    bounce_cap_pct: float = 0.05,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {-1,0} short/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=close.index)

    vol_avg20 = volume.rolling(20).mean()
    decline_ret = close / close.shift(decline_window) - 1.0
    decline_vol_avg = volume.rolling(decline_window).mean()

    sharp_decline = (decline_ret <= -decline_pct) & (decline_vol_avg >= decline_vol_ratio * vol_avg20)

    decline_low = close.rolling(decline_window).min()

    bounce_gain = close / decline_low - 1.0
    weak_bounce = (bounce_gain > 0) & (bounce_gain <= bounce_cap_pct) & (volume < vol_avg20)

    entry_signal = (sharp_decline.shift(1).fillna(False)) & weak_bounce

    entry = entry_signal.to_numpy()
    close_arr = close.to_numpy()
    decline_low_arr = decline_low.to_numpy()

    position = pd.Series(0, index=close.index, dtype=int)
    pos_arr = position.to_numpy().copy()

    in_position = False
    hold_days = 0
    bounce_high = None
    stop_buffer = 1.03  # 3% stop above bounce high
    for i in range(len(close)):
        if in_position:
            hold_days += 1
            new_low = close_arr[i] < decline_low_arr[i]
            stopped_out = bounce_high is not None and close_arr[i] > bounce_high * stop_buffer
            if new_low or stopped_out or hold_days >= max_hold_days:
                in_position = False
                hold_days = 0
                bounce_high = None
                pos_arr[i] = 0
            else:
                pos_arr[i] = -1
        else:
            if entry[i]:
                in_position = True
                hold_days = 0
                bounce_high = close_arr[i]
                pos_arr[i] = -1
            else:
                pos_arr[i] = 0

    position = pd.Series(pos_arr, index=close.index, dtype=int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    decline_window: int = 3,
    decline_pct: float = 0.04,
    decline_vol_ratio: float = 1.05,
    bounce_cap_pct: float = 0.05,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        decline_window=decline_window,
        decline_pct=decline_pct,
        decline_vol_ratio=decline_vol_ratio,
        bounce_cap_pct=bounce_cap_pct,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change()
    strat_ret = position.shift(1).fillna(0) * daily_ret
    strat_ret = strat_ret.fillna(0.0)
    return strat_ret
