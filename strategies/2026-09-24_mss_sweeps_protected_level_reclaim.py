"""Strategy: MSS (Market Structure Shift) Sweeps -- BOS-protected-level
sweep-and-reclaim continuation entry (long side only).

Hypothesis (knowledge_base id TBD, this cron trigger):
Per LuxAlgo's "MSS Sweeps" indicator
(https://www.luxalgo.com/library/indicator/mss-sweeps, read this iteration
via browser_exec -- web_search DDGS/Yahoo backend TLS-erroring on queries
attempted this iteration): after a Break of Structure (BOS) confirms an
uptrend (a close breaking above the most recent internal swing high), the
most recent internal swing LOW becomes a "protected level" (higher low).
A valid continuation signal fires when price later dips BELOW that
protected higher low intra-bar but RECLAIMS it (closes back above) on the
SAME bar -- a same-bar sweep-and-reclaim of a level the market structure
itself has already marked as significant, distinct from every other
liquidity-sweep entry in this repo (2026-09-09-087/089, 2026-09-23-046/047,
2026-09-24 iteration 4 this trigger's RSI-divergence rescue, this trigger's
iteration 5 AMD-POC) which all swept a plain rolling N-bar low/high or a
volume-profile level, never a level whose significance comes specifically
from being the pivot BEHIND a just-confirmed BOS. This is also distinct
from this repo's existing BOS/CHoCH entries (2026-09-24 iterations
"choch_market_structure_shift" and "bos_trend_continuation_retest" from
earlier this cron trigger) which traded the BOS breakout bar itself or a
pullback/retest of the broken level -- never a sweep-and-reclaim of the
NEW higher-low the BOS creates.

Signal logic (long side only)
------------------------------
- Internal pivots: rolling `swing_window`-bar fractal highs/lows (a bar is
  a pivot high/low if it's the max/min of its trailing+leading window,
  approximated here with a simple trailing-only pivot since no look-ahead
  is allowed for live signal generation).
- BOS: a close breaking above the most recent confirmed internal swing
  high marks an uptrend confirmation; the most recent internal swing LOW
  formed since the prior BOS becomes the "protected level".
- MSS sweep-and-reclaim: on a later bar (before the protected level is
  itself broken/invalidated), low < protected_level (intrabar sweep) AND
  close > protected_level (same-bar reclaim) triggers a long entry.
- Exit: close falls back below the protected level (structure
  invalidated), OR a max_hold_days time-stop.
- Optional close>SMA(trend_window) higher-timeframe uptrend gate (default
  True).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    return df.sort_index()


def _pivot_highs_lows(df: pd.DataFrame, swing_window: int):
    """Confirmed fractal pivots with a lag (no look-ahead at the time of
    confirmation, but the pivot itself is `swing_window` bars in the past
    once confirmed): bar (i - swing_window) is a pivot high if it is the
    max of the window [i - 2*swing_window, i] (centered fractal, but only
    "known" once the right-hand side bars have printed). This avoids the
    degenerate trailing-only case where the most recent bar is trivially
    its own rolling max during a trend and a BOS condition (close >
    swing high) can never fire because the "swing high" is always the
    live bar itself.
    """
    high = df["high"]
    low = df["low"]
    window = 2 * swing_window + 1
    rolling_max = high.rolling(window, center=True).max()
    rolling_min = low.rolling(window, center=True).min()
    is_pivot_high_raw = (high == rolling_max)
    is_pivot_low_raw = (low == rolling_min)
    # Shift forward by swing_window bars so the pivot is only "seen" once
    # confirmed (i.e. once the trailing swing_window bars after it exist).
    is_pivot_high = is_pivot_high_raw.shift(swing_window).fillna(False).astype(bool)
    is_pivot_low = is_pivot_low_raw.shift(swing_window).fillna(False).astype(bool)
    return is_pivot_high, is_pivot_low


def generate_signals(
    price_df: pd.DataFrame,
    swing_window: int = 5,
    max_hold_days: int = 15,
    trend_window: int = 200,
    trend_filter: bool = True,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    n = len(df)

    is_pivot_high, is_pivot_low = _pivot_highs_lows(df, swing_window)
    sma_trend = close.rolling(trend_window).mean()
    uptrend = (close > sma_trend).fillna(False) if trend_filter else pd.Series(True, index=close.index)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    last_swing_high = None
    last_swing_low = None
    protected_level = None
    bos_confirmed = False

    i = swing_window
    while i < n:
        # Track internal pivots as they form.
        if bool(is_pivot_high.iloc[i]):
            last_swing_high = high.iloc[i]
        if bool(is_pivot_low.iloc[i]):
            # A new swing low forming AFTER a BOS becomes the new protected level.
            last_swing_low = low.iloc[i]
            if bos_confirmed:
                protected_level = last_swing_low

        # Break of Structure: close breaks above the last known swing high.
        if last_swing_high is not None and close.iloc[i] > last_swing_high and not bos_confirmed:
            bos_confirmed = True
            protected_level = last_swing_low  # the pivot low behind this BOS

        if in_position:
            held = i - entry_idx
            invalidated = protected_level is not None and close.iloc[i] < protected_level
            if invalidated or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                i += 1
                continue
            position.iloc[i] = 1
            i += 1
            continue

        # MSS sweep-and-reclaim entry.
        if (
            bos_confirmed
            and protected_level is not None
            and bool(uptrend.iloc[i])
            and low.iloc[i] < protected_level
            and close.iloc[i] > protected_level
        ):
            in_position = True
            entry_idx = i
            position.iloc[i] = 1
            i += 1
            continue

        position.iloc[i] = 0
        i += 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
