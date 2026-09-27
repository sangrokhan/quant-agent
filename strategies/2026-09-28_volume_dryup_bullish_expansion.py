"""Strategy: Volume Dry-up bullish-expansion breakout long.

Hypothesis (source: https://www.luxalgo.com/library/indicator/volume-dry-up/,
read 2026-09-28 via browser_exec while browsing LuxAlgo's Volume & Order
Flow family listing for a fresh angle after VP-MACD/Composite Momentum
Index web_search queries turned up nothing new -- 0 prior hits for
"Volume Dry-up" in strategies_index.jsonl):

LuxAlgo's Volume Dry-up detector finds sessions where turnover quietly
disappears (source: "the volume dry-up growth-stock methods read as supply
exhaustion") -- a session qualifies as a dry-up when volume prints at or
below `dryup_threshold` (default 0.5) of its `vol_baseline`-bar (default
50) rolling average, optionally requiring the bar's own high-low spread to
also be contracted relative to its own rolling average (source's "Range
Contraction" toggle). Once a dry-up session prints, the indicator "arms a
resolution window" of `resolution_window` bars (default 5): a decisive
Bullish Expansion is an up-close bar with volume >= `expansion_multiple`
(default 1.5) times the baseline average occurring within that window --
source's own words: "an up close on at least 1.5x average volume inside
the window, the constructive resolution."

This is a genuinely distinct construction from every prior volatility/
volume-compression breakout already tested in this repo (Donchian, Darvas
Box, ATR-expansion, TTM Squeeze, Bollinger Bandwidth squeeze, and
Minervini's VCP 2026-09-06-111): those all key off price-range compression
directly or (VCP) a multi-leg monotonically-shallowing pullback sequence.
Volume Dry-up keys off a single quiet-volume session (a supply-exhaustion
read) followed within a short window by a confirmed high-volume up-close
(the "expansion that answers it"), which is a fundamentally different
detection mechanism (event + short confirmation window, not a persistent
compression state).

Hypothesis: on a daily-bar basis, a confirmed Volume Dry-up -> Bullish
Expansion sequence (dormancy exhausts supply, then genuine buying volume
resolves it upward) marks a higher-quality long entry than a plain
volume-spike breakout with no preceding dormancy, because the dry-up phase
specifically signals sellers have stepped away rather than merely that
volume is currently elevated.

Signal logic (daily-bar mechanical proxy for source's full detector):
- baseline_vol = rolling mean(volume, vol_baseline).
- baseline_spread = rolling mean(high - low, vol_baseline).
- dry_up = (volume <= dryup_threshold * baseline_vol) AND
  ((high - low) <= range_contraction_frac * baseline_spread) (source's
  Range Contraction toggle, kept enabled per source default).
- Within `resolution_window` bars after a dry_up bar, a Bullish Expansion
  fires on the first bar where: close > open (up-close) AND
  volume >= expansion_multiple * baseline_vol.
- Entry: long at the close of the Bullish Expansion bar (if not already
  in a position).
- Exit: close below the dry-up bar's own low (source's read: the
  constructive resolution failed / supply came back), OR a max_hold_days
  time-stop -- whichever comes first.

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
    vol_baseline: int = 50,
    dryup_threshold: float = 0.5,
    range_contraction_frac: float = 1.0,
    expansion_multiple: float = 1.5,
    resolution_window: int = 5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    baseline_vol = volume.rolling(vol_baseline).mean()
    spread = high - low
    baseline_spread = spread.rolling(vol_baseline).mean()

    dry_up = (volume <= dryup_threshold * baseline_vol) & (
        spread <= range_contraction_frac * baseline_spread
    )
    up_close = close > open_
    expansion_ok = volume >= expansion_multiple * baseline_vol

    n = len(df)
    dry_up_arr = dry_up.fillna(False).to_numpy()
    up_close_arr = up_close.to_numpy()
    expansion_ok_arr = expansion_ok.fillna(False).to_numpy()
    low_arr = low.to_numpy()
    close_arr = close.to_numpy()

    pos = pd.Series(0.0, index=df.index)
    in_pos = False
    hold_count = 0
    stop_level = np.nan
    pending_dryup_idx = -1  # index of last unresolved dry-up bar

    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_now = (close_arr[i] < stop_level) or (hold_count >= max_hold_days)
            if exit_now:
                in_pos = False
                hold_count = 0
                stop_level = np.nan
            else:
                pos.iloc[i] = 1.0

        if not in_pos:
            # Check if today resolves a pending dry-up as a bullish expansion.
            if (
                pending_dryup_idx >= 0
                and i - pending_dryup_idx <= resolution_window
                and bool(up_close_arr[i])
                and bool(expansion_ok_arr[i])
            ):
                in_pos = True
                hold_count = 0
                stop_level = low_arr[pending_dryup_idx]
                pos.iloc[i] = 1.0
                pending_dryup_idx = -1
            elif pending_dryup_idx >= 0 and i - pending_dryup_idx > resolution_window:
                pending_dryup_idx = -1

        if bool(dry_up_arr[i]):
            pending_dryup_idx = i

    return pos


def generate_returns(
    price_df: pd.DataFrame,
    vol_baseline: int = 50,
    dryup_threshold: float = 0.5,
    range_contraction_frac: float = 1.0,
    expansion_multiple: float = 1.5,
    resolution_window: int = 5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return the daily strategy return series (no transaction costs)."""
    df = _prep(price_df)
    pos = generate_signals(
        df,
        vol_baseline=vol_baseline,
        dryup_threshold=dryup_threshold,
        range_contraction_frac=range_contraction_frac,
        expansion_multiple=expansion_multiple,
        resolution_window=resolution_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0.0)
    return strat_ret
