"""Strategy: High and Tight Flag (Bulkowski) breakout continuation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-017):
Per Thomas Bulkowski's High & Tight Flag study
(https://thepatternsite.com/HTFStudy.html): a "high and tight flag"
requires price to rise at least 90% (lowest low to highest high) within
42 price bars (2 calendar months) -- the "flagpole" -- with no single-day
spike doing all the work. After the flagpole's peak (highest high before
price drops 20% from that high), the pattern's "flag" is the subsequent
consolidation; a breakout occurs when price closes at least a penny above
the flagpole top. Source's own disclosed stop reference: "a penny below
the flag low" (operationalized here as the lowest close during the flag
consolidation window). Source's own quick-results table: 61% of patterns
found the "ultimate high" (a further run before a 20% pullback), 18%
dropped to the flag low first (average loss 10% for those), 14% broke out
downward entirely (excluded here since this strategy only trades the
confirmed upward breakout).

Operationalized mechanically for daily bars:
  1. Flagpole detection: within a rolling `flagpole_window`-bar window,
     the ratio of the window's highest high to its lowest low must be
     >= `flagpole_pct` (default 1.90, i.e. 90% rise) AND the lowest low
     must occur at or before the highest high (rise, not fall).
  2. Flag consolidation: after the flagpole's peak, wait up to
     `flag_max_bars` for the "flag" to form (source's own median flag
     duration is short -- days to a few weeks). Track the flag's lowest
     close as the stop reference.
  3. Breakout entry: long when close breaks above the flagpole's peak
     high (source's own "a penny above the top of the flagpole" rule)
     within `flag_max_bars` of the peak.
  4. Exit: close crossing below the flag's lowest close recorded during
     consolidation (source's own stop reference), OR a max_hold_days
     time-stop (source's own 20%-drawdown-from-high "ultimate high" exit
     approximated here as a fixed hold since intrabar high-tracking for a
     trailing 20% exit is out of scope for a first pass).

First High & Tight Flag strategy in this repo -- distinct from
already-tested Cup-and-Handle (2026-09-06-172, requires a much slower
7-65-WEEK rounded correction+handle, not a fast 90%-in-42-bars impulsive
flagpole) and Bull Flag (2026-09-08-130, no minimum flagpole magnitude
requirement at all -- any "strong up-move" qualifies, whereas HTF requires
a specific, extreme 90%+ move).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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
    flagpole_window: int = 42,
    flagpole_pct: float = 1.90,
    flag_max_bars: int = 20,
    max_hold_days: int = 40,
) -> pd.Series:
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]
    n = len(df)

    rolling_high = high.rolling(flagpole_window).max()
    rolling_low = low.rolling(flagpole_window).min()
    # index of the rolling low and rolling high within the window (via argmin/argmax)
    low_pos = low.rolling(flagpole_window).apply(lambda x: x.values.argmin(), raw=False)
    high_pos = high.rolling(flagpole_window).apply(lambda x: x.values.argmax(), raw=False)

    flagpole_ratio = rolling_high / rolling_low.replace(0, np.nan)
    is_flagpole = (flagpole_ratio >= flagpole_pct) & (low_pos <= high_pos)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    entry_idx = -1
    stop_level = np.nan
    idx_list = df.index.tolist()

    # track pending flagpole peaks awaiting breakout within flag_max_bars
    pending_peak_price = None
    pending_peak_idx = -1

    for i in range(flagpole_window, n):
        ts = idx_list[i]

        if not in_pos:
            # register a new pending flagpole if detected at this bar
            if bool(is_flagpole.iloc[i]):
                peak_price = rolling_high.iloc[i]
                # only register if this is a fresh/higher flagpole peak
                if pending_peak_price is None or peak_price > pending_peak_price:
                    pending_peak_price = peak_price
                    pending_peak_idx = i

            if pending_peak_price is not None:
                bars_since_peak = i - pending_peak_idx
                if bars_since_peak > flag_max_bars:
                    # flag window expired without breakout
                    pending_peak_price = None
                    pending_peak_idx = -1
                elif close.iloc[i] > pending_peak_price:
                    # breakout confirmed
                    flag_slice = close.iloc[pending_peak_idx:i + 1]
                    stop_level = flag_slice.min()
                    in_pos = True
                    entry_idx = i
                    pending_peak_price = None
                    pending_peak_idx = -1
        else:
            days_held = i - entry_idx
            stop_hit = close.iloc[i] < stop_level
            if stop_hit or days_held >= max_hold_days:
                in_pos = False
            else:
                position.loc[ts] = 1

        if in_pos and i >= entry_idx:
            position.loc[ts] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(price_df, **params)
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    return strat_returns
