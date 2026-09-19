"""Strategy: DXY (US Dollar Index) absolute-level hysteresis regime gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-026):
Per multiple 2026 dollar/crypto macro explainers (e.g.
https://www.neverhodl.com/intelligence/learn/dxy-dollar-index-bitcoin), the
DXY has well-known absolute-level "zones": DXY<90 = weak dollar / most
favorable risk-asset regime (both the 2017 and 2020-2021 BTC bull runs
occurred with DXY<90); DXY 90-100 = neutral; DXY>105 = "significant
headwind" (2022 bear market coincided with DXY reaching 114). This is
distinct from every prior DXY strategy in this repo:
  - 2026-09-05-026 (rejected): DXY vs its OWN 50d SMA (relative, re-evaluated
    every bar, no hysteresis).
  - 2026-09-09-113 (rejected): DXY rate-of-change momentum gate (relative
    change, not absolute level).
  - 2026-09-11-058 (accepted SPY/QQQ): UUP vs its own SMA trend gate (a
    dollar ETF proxy trend-following construction, not DXY absolute levels).
None of these used FIXED ABSOLUTE DXY LEVELS as a two-level hysteresis state
machine (enter risk-on long when DXY closes below a low absolute threshold,
exit back to flat only when DXY closes back above a much higher absolute
threshold) -- the exact construction pattern already validated as a distinct,
testable idea for VIX in this repo (2026-09-20-009/2026-09-20 vix_absolute
_level_hysteresis_regime.py). Applying that same state-machine construction
to DXY's own disclosed absolute zones is the novel angle this iteration
tests, on both equities (SPY/QQQ) and crypto (BTC/ETH, since the source's
own economic rationale -- global dollar liquidity -- is explicitly framed as
a crypto-relevant macro driver, arguably even more directly than for
equities).

Signal logic
------------
- Load ^DXY-proxy "DX-Y.NYB" daily close (yfinance ICE US Dollar Index
  continuous future) via data/loaders.py, reindexed/ffilled onto the traded
  asset's own daily index.
- State machine: once DXY closes below `enter_level` (weak-dollar / risk-on
  trigger), go/stay LONG the traded asset, regardless of subsequent DXY
  wiggles, until DXY closes back above `exit_level` (a higher absolute
  level -- the "significant headwind" zone), at which point go/stay FLAT
  until DXY drops below `enter_level` again.
- No dependence on any other indicator -- pure DXY absolute level.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

_dxy_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_dxy_close(index: pd.DatetimeIndex) -> pd.Series:
    """Load DX-Y.NYB (ICE US Dollar Index continuous future) close,
    reindexed/ffilled to the primary asset's index. Cached across calls
    within a process."""
    if "dxy" in _dxy_cache:
        dxy_close = _dxy_cache["dxy"]
    else:
        from loaders import load_equity

        start = index.min().to_pydatetime() if len(index) else datetime(2015, 1, 1)
        end = index.max().to_pydatetime() if len(index) else datetime(2026, 9, 1)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        pad_start = start.replace(year=max(start.year - 2, 2005))

        dxy_df = _prep(load_equity("DX-Y.NYB", pad_start, end))
        dxy_close = dxy_df["close"]
        _dxy_cache["dxy"] = dxy_close

    reindexed = dxy_close.reindex(index, method="ffill")
    return reindexed


def _hysteresis_state_inverse(dxy: pd.Series, enter_level: float, exit_level: float) -> pd.Series:
    """Two-level hysteresis, INVERSE direction vs the VIX version: once DXY
    closes BELOW enter_level (weak dollar), state flips to 1 (long) and
    STAYS 1 regardless of intermediate DXY values until DXY closes ABOVE
    exit_level (strong-dollar headwind zone), at which point state flips to
    0 (flat) and stays 0 until DXY drops below enter_level again."""
    dxy_arr = dxy.to_numpy()
    n = len(dxy_arr)
    state = np.zeros(n, dtype=int)
    cur = 0
    for i in range(n):
        v = dxy_arr[i]
        if np.isnan(v):
            state[i] = cur
            continue
        if cur == 0 and v < enter_level:
            cur = 1
        elif cur == 1 and v > exit_level:
            cur = 0
        state[i] = cur
    return pd.Series(state, index=dxy.index)


def generate_signals(
    price_df: pd.DataFrame,
    enter_level: float = 100.0,
    exit_level: float = 105.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long from the first DXY close < enter_level (weak dollar / risk-on),
    held until DXY closes above exit_level (strong-dollar headwind zone),
    two-level hysteresis, no re-evaluation in between.
    """
    df = _prep(price_df)
    dxy = _load_dxy_close(df.index)
    position = _hysteresis_state_inverse(dxy, enter_level, exit_level)
    position.index = df.index
    return position.astype(int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
