"""Strategy: OBV Bullish Divergence Reversal with EMA-crossback trigger.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-088):
Per arrowalgo.com's mechanical OBV divergence rule set: On-Balance Volume
(Joe Granville, 1963, cumulative running total of +/-volume on up/down
close days) tracks buying/selling conviction independent of price. A
bullish divergence occurs when price makes a new N-bar low while OBV does
NOT make a new N-bar low (selling pressure drying up even as price
slips) -- a setup, not a trigger. The mechanical trigger is a price
close back above a short EMA, confirming the reversal has begun; stop
below the divergence low. Distinct from the previously-tested
2026-09-04-027 (OBV as a simple confirmation FILTER on top of a separate
breakout signal) -- this is a genuine two-series divergence comparison
(rolling price extreme vs. rolling OBV extreme) with its own EMA trigger.

Signal logic
------------
- OBV = cumulative sum of (+volume on up-close days, -volume on
  down-close days, 0 on unchanged)
- Bullish divergence setup: close == rolling min(close, window) (a fresh
  N-bar low) AND OBV > rolling min(OBV, window) (OBV did NOT make a new
  low -- divergence).
- Entry (long): once a divergence setup has fired within the last
  `lookahead` bars, entry triggers when close crosses back above
  EMA(ema_window).
- Exit: after `max_hold_days`, or if close drops back below the
  divergence-low stop level, whichever first.
- Long-only, flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff()).fillna(0.0)
    return (direction * volume).cumsum()


def generate_signals(
    price_df: pd.DataFrame,
    window: int = 40,
    ema_window: int = 10,
    lookahead: int = 10,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    obv = _obv(close, volume)
    close_roll_min = close.rolling(window).min()
    obv_roll_min = obv.rolling(window).min()

    price_new_low = close <= close_roll_min
    obv_not_new_low = obv > obv_roll_min
    divergence_setup = (price_new_low & obv_not_new_low).fillna(False)

    ema = close.ewm(span=ema_window, adjust=False).mean()
    cross_above_ema = (close > ema) & (close.shift(1) <= ema.shift(1))

    # divergence low level (for stop) carried forward from the most recent setup
    divergence_low = close.where(divergence_setup).ffill()
    bars_since_setup = (~divergence_setup).groupby(divergence_setup.cumsum()).cumcount()

    entry_trigger = (
        cross_above_ema & (bars_since_setup <= lookahead) & divergence_low.notna()
    )

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    stop_level = None
    for i in range(n):
        if in_pos:
            hold_count += 1
            stopped = close.iloc[i] < stop_level if stop_level is not None else False
            if hold_count >= max_hold_days or stopped:
                in_pos = False
                position.iloc[i] = 0
                stop_level = None
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
                in_pos = True
                hold_count = 0
                stop_level = divergence_low.iloc[i]
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    window: int = 40,
    ema_window: int = 10,
    lookahead: int = 10,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df, window=window, ema_window=ema_window, lookahead=lookahead, max_hold_days=max_hold_days
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
