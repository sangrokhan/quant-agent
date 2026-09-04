"""Strategy: Yield-Curve Un-Inversion Bear Signal (10Y-3M Treasury spread).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-024),
sourced from multiple converging web sources (Morningstar "What Investors
Need to Know About the Steepening Yield Curve", CNBC 2019-06-27 "Yield
curve rapid steepening may be sending recession signal", BIS working paper
on yield curve inversion/recession risk, and general financial press
consensus): the 10-Year minus 3-Month Treasury yield spread (T10Y3M)
inverting (going negative) has preceded every US recession since 1973, but
critically the equity-market damage/recession itself has historically
occurred AFTER the curve UN-inverts (the spread crosses back from negative
to positive, i.e. the curve "steepens" again) rather than during the
inversion itself -- the inversion is priced as "recession risk", but the
un-inversion/steepening is when the Fed cutting rates in response to
weakening data or a real economic downturn actually shows up. This is
DIFFERENT from a naive "short when curve is inverted" rule -- it's a
timing signal on the TRANSITION out of inversion.

Signal logic
------------
- Default long-only position (buy and hold the underlying).
- Fetches ^TNX (10-Year Treasury yield, CBOE index) and ^IRX (13-week /
  3-month T-bill yield) via data/loaders.py load_equity internally (not
  passed through generate_returns_fn's price_df -- same pattern as this
  repo's other cross-asset VIX-based strategies).
- Compute spread = TNX - IRX daily. Track whether the spread has been
  inverted (spread < 0) at any point in the trailing `lookback_days`
  trading days. A "un-inversion" event fires on the day the spread
  crosses from negative to >= `uninvert_threshold` (default 0, i.e. back
  to non-negative) after having been inverted within that lookback window.
- Go FLAT (exit to cash) for `flat_window_days` trading days starting the
  day after an un-inversion event; long otherwise.
- Tested on equity (QQQ, SPY -- where the mechanism, US recession risk
  pricing, plausibly applies) and crypto (BTC/USDT, ETH/USDT) as a
  falsification / spillover check.

Interface contract for validators (see validation/validators.py) and grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
"""

from __future__ import annotations

import sys
import os
from datetime import datetime, timedelta

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
    lookback_days: int = 60,
    uninvert_threshold: float = 0.0,
    flat_window_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long by default; flat for `flat_window_days` trading days after the
    10Y-3M Treasury spread un-inverts (crosses from negative to
    >= uninvert_threshold) having been inverted at some point within the
    trailing `lookback_days` trading days.
    """
    df = _prep(price_df)
    idx = df.index

    try:
        spread = _get_yield_spread(idx)
    except Exception:
        # Data unavailable (e.g. crypto symbols traded on a different
        # calendar with sparse ^TNX/^IRX coverage) -- default to always-long
        # (no signal fires), which effectively makes this a
        # buy-and-hold no-op for that symbol, correctly failing to show
        # any edge rather than crashing the grid.
        return pd.Series(1, index=idx, dtype=int)

    was_inverted_recently = (spread < 0).rolling(lookback_days, min_periods=1).max().astype(bool)
    is_uninverted_now = spread >= uninvert_threshold
    prev_was_inverted = was_inverted_recently.shift(1).fillna(False)
    uninvert_event = is_uninverted_now & prev_was_inverted & ~(spread.shift(1) >= uninvert_threshold).fillna(False)

    position = pd.Series(1, index=idx, dtype=int)
    event_positions = [i for i, v in enumerate(uninvert_event.values) if v]
    for pos in event_positions:
        start_i = pos + 1
        end_i = min(pos + 1 + flat_window_days, len(idx))
        position.iloc[start_i:end_i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    # Shift position by 1 day: yesterday's signal determines today's exposure
    # (avoid look-ahead bias -- can't trade on today's own close).
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
