"""Strategy: Yield Curve Inversion Event -> Buy-and-Hold N Days (Contrarian).

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD, source
https://www.quantifiedstrategies.com/yield-inversion-trading-strategy/,
"Yield curve inversion strategy backtest no. 1"):

QuantifiedStrategies' own disclosed backtest #1 rule: "When the yield curve
gets inverted (i.e. crossing below zero), we buy S&P 500. We sell 250
trading days later." Their finding (S&P 500 cash index, since 1976): 11
trades, average gain over the next 250 days ~7.35% (similar to the
long-run average annual return), 63% win rate; holding 500 days instead
raises average gain to 18.3% (7 trades) -- both are ABOUT AS GOOD AS a
random 250/500-day holding period, i.e. the source's own conclusion is
that the inversion EVENT itself is not really a differentiated entry
signal, just a random-ish long-only entry that benefits from equities'
positive long-run drift.

This repo already has TWO other yield-curve strategies (un-inversion
timing-based flat-gate 2026-09-05-024/2026-09-10-041, and TNX-vs-own-SMA
crossover 2026-09-09-051), but NEITHER tests this specific "buy exactly
at the inversion EVENT and hold a fixed N-day window" construction --
distinct because (a) it's event-triggered rather than a continuous
regime gate, (b) it's a FIXED holding period (not exited on any
signal-based condition), and (c) it directly tests the source's own
explicit, disclosed backtest rule rather than a derived/combined variant.

Signal logic
------------
- Fetches ^TNX (10Y) and ^IRX (13-week T-bill) via data/loaders.py
  internally (cross-asset macro signal pattern, same as this repo's other
  yield-curve strategies).
- spread = TNX - IRX. An inversion EVENT fires the day spread crosses from
  >=0 to <0 (debounced: while an inversion event's hold_days window is
  still open, no new event can fire -- avoids re-triggering on noisy
  boundary-crossing days within the same inversion episode, which this
  repo's earlier un-inversion strategy also had to guard against).
- On an inversion event, go long for `hold_days` trading days, then flat
  until the next NEW inversion event (only after fully exiting the prior
  hold window).
- Flat by default (not long-by-default like the un-inversion strategy) --
  this strategy is ONLY invested during the fixed post-event window,
  matching the source's literal buy-then-sell-N-days-later rule.

Interface contract for validators (see validation/validators.py) and
grid_test.py (Step 6): generate_signals/generate_returns both accept
tunable parameters as keyword arguments.
"""

from __future__ import annotations

import sys
import os

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_yield_spread(idx: pd.DatetimeIndex) -> pd.Series:
    """Fetch ^TNX and ^IRX and return the 10Y-3M spread reindexed/ffilled
    onto the strategy's own trading-day index."""
    from loaders import load_equity

    start = (idx.min() - pd.Timedelta(days=30)).to_pydatetime()
    end = (idx.max() + pd.Timedelta(days=5)).to_pydatetime()

    tnx = load_equity("^TNX", start, end)
    irx = load_equity("^IRX", start, end)

    tnx = tnx.set_index("timestamp")["close"].sort_index()
    irx = irx.set_index("timestamp")["close"].sort_index()

    spread = (tnx - irx).sort_index()
    spread.index = spread.index.tz_localize(None) if spread.index.tz is not None else spread.index

    target_idx = idx.tz_localize(None) if getattr(idx, "tz", None) is not None else idx
    spread = spread.reindex(spread.index.union(target_idx)).sort_index().ffill()
    spread = spread.reindex(target_idx)
    spread.index = idx
    return spread


def generate_signals(
    price_df: pd.DataFrame,
    hold_days: int = 250,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Flat by default. On a debounced yield-curve inversion event (spread
    crosses from >=0 to <0, only counted if not already in an active
    post-event hold window), go long for `hold_days` trading days, then
    flat until the next new event.
    """
    df = _prep(price_df)
    idx = df.index

    try:
        spread = _get_yield_spread(idx)
    except Exception:
        # Data unavailable (e.g. crypto's different calendar/sparse
        # ^TNX/^IRX coverage) -- default to always-flat (no signal fires),
        # correctly failing to show any edge rather than crashing the grid.
        return pd.Series(0, index=idx, dtype=int)

    is_inverted = (spread < 0).fillna(False)

    position = pd.Series(0, index=idx, dtype=int)
    n = len(idx)
    i = 0
    prev_inverted = False
    while i < n:
        cur_inverted = bool(is_inverted.iloc[i])
        if cur_inverted and not prev_inverted:
            # New (debounced) inversion event -- open a hold_days window.
            end_i = min(i + hold_days, n)
            position.iloc[i:end_i] = 1
            # Skip ahead past this hold window; re-arm debounce only after
            # the window closes (so no new event can fire mid-window).
            prev_inverted = cur_inverted
            i = end_i
            continue
        prev_inverted = cur_inverted
        i += 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    # Shift position by 1 day to avoid look-ahead bias.
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
