"""Strategy: VIX1D percentile-rank regime gate on SMA trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-038):
CBOE's VIX1D (1-Day Volatility Index, launched April 2023, per
https://volatilitybox.com/research/vix1d-explained/, read via
`browser_exec` this iteration after `web_search` surfaced it) measures
expected S&P 500 volatility over just the NEXT trading day (from SPX
options expiring the next business day), reacting far faster to
event-specific stress than the standard 30-day VIX ("VIX1D might read 22
while VIX sits at 15" on an event morning) and mean-reverting on the order
of hours to a day rather than days to weeks. This strategy tests whether a
standard SMA trend-following signal performs better when GATED to only
trade while VIX1D sits in its own LOW rolling-percentile regime (calm
near-term-event pricing), going flat when VIX1D spikes into its high
percentile (acute near-term stress priced in) -- the source's own
stated interpretation ladder (8-15 calm, 20-40 stress, 50+ panic). This is
the first VIX1D-specific strategy in this repo (0 prior KB hits for
"VIX1D") -- distinct from the repo's existing VIX-level, VIX-Bollinger-Band,
VIX9D:VIX ratio, and VIX/VIX3M term-structure strategies, all of which use
the 30-day-horizon VIX or its ratios, never the 1-day-horizon index.

VIX1D data (ticker `^VIX1D` via yfinance) only exists from its April 2023
launch, so this strategy's own data fetch is date-clamped to that
availability window regardless of the price_df's own date range (shorter
backtest window than most of this repo's other equity strategies, which
typically span 2019-2026).

Signal logic
------------
- Fetch ^VIX1D close series (own internal fetch via data/loaders.py,
  reused across calls via an in-process cache, same pattern as this
  repo's existing copper/gold-ratio and gold/silver-ratio regime
  strategies).
- Rolling percentile rank of VIX1D over `vix_lookback` days.
- Calm regime: percentile_rank <= calm_percentile (e.g. 40th percentile or
  below -- near-term event pricing is currently subdued).
- Entry (long): close > SMA(trend_window) AND calm regime.
- Exit: trend breaks (close <= SMA) OR regime flips to non-calm (VIX1D
  percentile rises above calm_percentile) OR max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity  # noqa: E402

_vix1d_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def _get_vix1d(start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    """Fetch ^VIX1D close series covering [start, end], cached. VIX1D data
    only exists from its April 2023 CBOE launch date."""
    key = (start.date().isoformat(), end.date().isoformat())
    if key in _vix1d_cache:
        return _vix1d_cache[key]

    launch = datetime(2023, 4, 24, tzinfo=timezone.utc)
    fetch_start = max(launch, datetime(start.year - 1, 1, 1, tzinfo=timezone.utc))
    fetch_end = datetime(end.year + 1, 1, 1, tzinfo=timezone.utc)

    vix1d = load_equity("^VIX1D", fetch_start, fetch_end)
    vix1d = vix1d.set_index(pd.to_datetime(vix1d["timestamp"], utc=True))["close"]
    vix1d = vix1d[~vix1d.index.duplicated(keep="first")].sort_index()
    _vix1d_cache[key] = vix1d
    return vix1d


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    vix_lookback: int = 252,
    calm_percentile: float = 0.4,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long when close > SMA(trend_window) AND VIX1D's rolling percentile
    rank is <= calm_percentile (near-term event pricing subdued). Exit on
    trend break, regime flip to non-calm, or a max_hold_days time-stop.
    """
    df = _prep(price_df)
    close = df["close"]
    idx = df.index

    vix1d_full = _get_vix1d(idx.min(), idx.max())
    vix1d = vix1d_full.reindex(idx, method="ffill").bfill()

    percentile_rank = vix1d.rolling(vix_lookback, min_periods=max(20, vix_lookback // 4)).apply(
        lambda w: (w <= w.iloc[-1]).mean(), raw=False
    )
    calm_regime = (percentile_rank <= calm_percentile).fillna(False)

    sma = close.rolling(trend_window).mean()
    trend_up = close > sma

    entry = trend_up & calm_regime
    exit_condition = (~trend_up) | (~calm_regime)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_condition.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
