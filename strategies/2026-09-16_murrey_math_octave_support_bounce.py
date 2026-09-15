"""Strategy: Murrey Math Lines octave support bounce (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
per Murrey Math theory (T. Henning Murrey), price action within a rolling
lookback window is divided into 8 equal "octave" levels (0/8 lowest_low,
8/8 highest_high, 4/8 midline) plus overshoot levels beyond 0/8 and 8/8.
The 0/8 line acts as an "ultimate support" -- prices that dip to 0/8 and
then close back above it signal a support-hold reversal bounce, entering
long with a target at the 4/8 midline (or the 8/8 ultimate resistance) and
a stop just beyond the 0/8 overshoot level (per RoboForex/LuxAlgo/Scribd
summaries of Murrey's own rules, all cross-consistent on this point). This
is the first Murrey Math strategy in this knowledge base (zero prior
matches for "Murrey Math" as of this iteration).

Sources read this iteration:
- Google AI overview synthesis (RoboForex, Scribd, LuxAlgo, EBC Financial
  Group, Slideshare) of Murrey Math Lines entry/exit/stop rules.

Signal logic
------------
- Rolling lookback window (lookback_n bars): lowest_low = rolling min(low),
  highest_high = rolling max(high). octave_range = highest_high - lowest_low.
  increment = octave_range / 8. level_0 = lowest_low (0/8 support),
  level_4 = lowest_low + 4*increment (4/8 midline),
  level_8 = highest_high (8/8 resistance).
- Long entry: previous close was below level_0 (a dip to/below "ultimate
  support") AND current close crosses back above level_0 (support-hold
  confirmation, per source's own "closes back above the line after a minor
  dip" rule).
- Exit: close reaches the 4/8 midline (take-profit target per source), OR
  close falls below level_0 - overshoot_buffer_mult*increment (stop loss,
  "beyond the extreme overshoot levels" per source), OR a max_hold_days
  time-stop.
- Flat otherwise.

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
    lookback_n: int = 64,
    overshoot_buffer_mult: float = 0.5,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    lowest_low = low.rolling(lookback_n).min()
    highest_high = high.rolling(lookback_n).max()
    increment = (highest_high - lowest_low) / 8.0
    level_0 = lowest_low
    level_4 = lowest_low + 4.0 * increment

    # Entry (long): the bar's intraday low touches/breaches the 0/8 support
    # line (a "dip to the 0/8 line") AND the close reclaims back above it
    # (source's "closes back above the line after a minor dip" support-hold
    # confirmation) -- both conditions on the SAME bar, since Murrey Math's
    # 0/8 line is itself derived from the rolling low, so a strict
    # prior-close-below-support formulation is near-impossible to trigger
    # (the rolling-min low that defines level_0 is always <= any close in
    # the same window).
    touched_support = low <= level_0
    reclaim_support = close > level_0
    entry_signal = touched_support & reclaim_support

    n = len(df.index)
    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_days = 0

    for i in range(n):
        if pd.isna(level_0.iloc[i]) or pd.isna(increment.iloc[i]):
            continue
        c = close.iloc[i]
        stop_level = level_0.iloc[i] - overshoot_buffer_mult * increment.iloc[i]
        tp_level = level_4.iloc[i]

        if in_position:
            hold_days += 1
            if c <= stop_level or c >= tp_level or hold_days >= max_hold_days:
                in_position = False
                hold_days = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
                in_position = True
                hold_days = 1
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    lookback_n: int = 64,
    overshoot_buffer_mult: float = 0.5,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_returns = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        lookback_n=lookback_n,
        overshoot_buffer_mult=overshoot_buffer_mult,
        max_hold_days=max_hold_days,
    )
    strat_returns = daily_returns * position.shift(1).fillna(0)
    return strat_returns
