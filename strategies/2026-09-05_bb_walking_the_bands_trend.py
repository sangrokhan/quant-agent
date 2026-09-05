"""Strategy: Bollinger Bands "Walking the Bands" trend-continuation
(John Bollinger), long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-084):
Per John Bollinger's own "Walking the Bands" concept (via tavifinance.com's
chapter summary of Bollinger's writing): "This chapter explores the concept
of 'walking the bands,' where the price repeatedly touches or stays close
to the upper or lower bands during a strong trend... Walking the bands is
indicative of a strong trend... When price continuously 'walks' the upper
band, it suggests that the market is in a powerful uptrend... this is NOT a
signal for reversal but rather a confirmation of trend strength. Traders
are advised to ride the trend until there is a clear indication of a
reversal... Traders should stay in the trade as long as the price continues
to walk the bands, exiting only when there are clear reversal signals."
This is fundamentally different from every prior Bollinger Band strategy in
this repo, which all treat a band touch/breach as a MEAN-REVERSION or
one-off BREAKOUT trigger (e.g. 2026-09-03-001 lower-band touch mean
reversion, 2026-09-04-091/126 squeeze-breakout). Here, close proximity to
the UPPER band across MULTIPLE consecutive bars is itself the TREND-
CONTINUATION confirmation signal, and the exit trigger is the price
"breaking away" from the band (dropping back inside, toward the middle
band) rather than any single-bar crossing event.

Signal logic
------------
- Bollinger Bands(bb_window, bb_std): SMA basis, upper = basis +
  bb_std*rolling_std, lower = basis - bb_std*rolling_std.
- "Walking the upper band": close >= upper_band * proximity_pct (e.g. 98%
  of the way to/at or above the upper band) for walk_bars consecutive bars.
- Entry (long): the walk_bars-consecutive-bar walking-the-upper-band
  condition is satisfied.
- Exit: close falls back below the basis (middle) band -- "breaking away"
  from the band, per source -- or a max_hold_days time-stop.
- Flat otherwise.

Interface contract (RESEARCH_LOOP.md Step 5):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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
    bb_window: int = 20,
    bb_std: float = 2.0,
    proximity_pct: float = 0.98,
    walk_bars: int = 3,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    basis = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()
    upper = basis + bb_std * std

    near_upper = close >= (upper * proximity_pct)
    walking = near_upper.rolling(walk_bars).sum() >= walk_bars

    entry = walking.fillna(False) & (~walking.shift(1).fillna(False))
    exit_cond = close < basis

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    entry_vals = entry.to_numpy()
    exit_vals = exit_cond.fillna(False).to_numpy()

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_vals[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_vals[i]):
                in_position = True
                entry_idx = i
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
