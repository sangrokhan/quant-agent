"""Strategy: Turtle Soup liquidity-sweep reversal (fade the failed breakout).

Hypothesis (source: https://grandalgo.com/blog/ict-turtle-soup-strategy,
read 2026-09-28 via browser_exec after web_search DDGS backend returned
empty results for the Ehlers/Vortex/Donchian-width queries this iteration --
the Turtle Soup query itself returned via web_search):

"Turtle Soup" (Linda Raschke's original fade of the Turtle Traders' 20-day
breakout system, later folded into ICT's liquidity-sweep vocabulary) claims
that when price breaks a well-respected N-bar swing low/high, triggers the
stop-losses/breakout entries clustered there, but FAILS TO CONTINUE and
closes back inside the prior range within a few bars, that failure candle's
close is a high-probability reversal entry -- the breakout traders who
chased the sweep are now trapped and their forced exits fuel the reversal.
Source's own disclosed exact rules (long/failed-breakdown side):
  1. Reference level = a swing low that has held for `swing_lookback` bars
     (source used a "clean 20-bar low", matching the original Turtle system).
  2. Price trades below that low (the sweep).
  3. Wait for a candle to close back ABOVE the swept level (the reclaim --
     no close back inside, no trade).
  4. Entry at that reclaim candle's close.
  5. Stop-loss below the sweep extreme (the lowest low reached during the
     sweep), not the original swing low itself (source explicitly warns
     against placing the stop at the "obvious" swing-low price, since that's
     the same pool that just got raided).
  6. Targets: first target = midpoint of the prior N-bar range; final target
     = opposite side of the range. We use a configurable R-multiple target
     off the stop distance instead (repo convention, since "opposite side of
     the range" isn't crisply computable from daily OHLCV alone), plus a
     max_hold_days time-stop (source doesn't disclose one; every other
     mean-reversion/reversal strategy in this repo uses one to avoid
     indefinite holds).

Short side (failed breakout of a swing high) is the mirror image but this
strategy is implemented long-only per repo convention (consistent with the
other long-only reversal strategies already in strategies/).

First Turtle-Soup / liquidity-sweep-reversal strategy in this repo (0 prior
hits for "Turtle Soup", "liquidity sweep", "false breakout reversal" in
strategies_index.jsonl) -- distinct from the many trend-following Donchian/
Turtle-style breakout strategies already tested here (which trade WITH the
breakout) and from the candlestick-reversal family (which key off candle
body shapes, not a specific N-bar swing-level sweep-and-reclaim sequence).

Signal logic
------------
- Reference low = rolling min of `low` over `swing_lookback` days, computed
  on data EXCLUDING the current bar (shifted by 1) so today's own low can't
  set its own reference level.
- Sweep bar: today's low < reference low (price traded below the swing low).
- Reclaim bar: within `reclaim_window` bars after (and including) a sweep
  bar, the FIRST bar whose close > reference low is the entry trigger
  (entry at that bar's close). If no reclaim happens within
  `reclaim_window` bars, the setup is abandoned (no trade for that sweep).
- Stop-loss = lowest low reached from the sweep bar through the reclaim bar
  (the sweep extreme), minus a tiny buffer handled implicitly by using the
  low itself (repo's other R-multiple strategies do the same).
- Take-profit = entry + reward_r_multiple * (entry - stop).
- Time-stop: exit after max_hold_days if neither stop nor target hit.
- Long-only, one position at a time (fully invested 0/1 while in a trade).

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


def _compute_trades(
    df: pd.DataFrame,
    swing_lookback: int,
    reclaim_window: int,
    reward_r_multiple: float,
    max_hold_days: int,
):
    """Scan bar-by-bar for sweep -> reclaim -> managed-trade sequences.

    Returns a list of (entry_idx, exit_idx, entry_price, exit_price) tuples
    using integer positions into df.
    """
    close = df["close"].to_numpy()
    low = df["low"].to_numpy()
    high = df["high"].to_numpy()
    n = len(df)

    ref_low = df["low"].rolling(swing_lookback).min().shift(1).to_numpy()

    trades = []
    i = 0
    in_position_until = -1  # index up to which we're already in a trade

    while i < n:
        if i <= in_position_until:
            i += 1
            continue
        if np.isnan(ref_low[i]):
            i += 1
            continue
        # Sweep bar: today's low breaks below the reference swing low.
        if low[i] < ref_low[i]:
            level = ref_low[i]
            sweep_extreme = low[i]
            reclaim_idx = None
            # Look for the first reclaim close within reclaim_window bars
            # (including the sweep bar itself, in case it closes back above).
            for j in range(i, min(i + reclaim_window, n)):
                sweep_extreme = min(sweep_extreme, low[j])
                if close[j] > level:
                    reclaim_idx = j
                    break
            if reclaim_idx is None:
                i += 1
                continue

            entry_idx = reclaim_idx
            entry_price = close[entry_idx]
            stop_price = sweep_extreme
            risk = entry_price - stop_price
            if risk <= 0:
                i = entry_idx + 1
                continue
            target_price = entry_price + reward_r_multiple * risk

            exit_idx = None
            exit_price = None
            for k in range(entry_idx + 1, min(entry_idx + 1 + max_hold_days, n)):
                if low[k] <= stop_price:
                    exit_idx = k
                    exit_price = stop_price
                    break
                if high[k] >= target_price:
                    exit_idx = k
                    exit_price = target_price
                    break
            if exit_idx is None:
                exit_idx = min(entry_idx + max_hold_days, n - 1)
                exit_price = close[exit_idx]

            trades.append((entry_idx, exit_idx, entry_price, exit_price))
            in_position_until = exit_idx
            i = exit_idx + 1
        else:
            i += 1

    return trades


def generate_signals(
    price_df: pd.DataFrame,
    swing_lookback: int = 20,
    reclaim_window: int = 3,
    reward_r_multiple: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    trades = _compute_trades(
        df, swing_lookback, reclaim_window, reward_r_multiple, max_hold_days
    )
    pos = pd.Series(0, index=df.index, dtype=float)
    for entry_idx, exit_idx, _, _ in trades:
        pos.iloc[entry_idx : exit_idx + 1] = 1.0
    return pos.reindex(price_df.index if "timestamp" not in price_df.columns else df.index).fillna(0.0)


def generate_returns(
    price_df: pd.DataFrame,
    swing_lookback: int = 20,
    reclaim_window: int = 3,
    reward_r_multiple: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return the daily strategy return series (no transaction costs)."""
    df = _prep(price_df)
    trades = _compute_trades(
        df, swing_lookback, reclaim_window, reward_r_multiple, max_hold_days
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = pd.Series(0.0, index=df.index)

    for entry_idx, exit_idx, entry_price, exit_price in trades:
        if exit_idx > entry_idx:
            # Hold the underlying's daily returns while in the trade,
            # from the bar after entry through the exit bar.
            strat_ret.iloc[entry_idx + 1 : exit_idx + 1] = daily_ret.iloc[
                entry_idx + 1 : exit_idx + 1
            ]
        # Entry-bar return: captured via the (entry_price vs prior close)
        # move already embedded in daily_ret at entry_idx+1 onward; the
        # entry bar itself (reclaim bar) contributes 0 here since we enter
        # AT its close (consistent with other repo strategies' convention).
        # Adjust the exit bar's return to reflect actual exit_price instead
        # of the raw close, when a stop/target triggered intrabar.
        exit_close = df["close"].iloc[exit_idx]
        if exit_close != 0 and exit_price != exit_close:
            prior_close = df["close"].iloc[exit_idx - 1] if exit_idx > 0 else df["close"].iloc[exit_idx]
            if prior_close != 0:
                strat_ret.iloc[exit_idx] = (exit_price / prior_close) - 1.0

    return strat_ret
