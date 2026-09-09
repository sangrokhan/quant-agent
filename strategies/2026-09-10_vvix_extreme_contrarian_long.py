"""Strategy: VVIX extreme-spike contrarian long on SPY/QQQ.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-022):
The CBOE VVIX Index (volatility of VIX, derived from VIX options) has a
long-term mean near 86 and a historical range of roughly 60-215. Per a
2026 VVIX trading guide, readings above 120 signal extreme fear that the
VIX itself will spike further, but historically these VVIX>120 extremes have
tended to mark PEAK uncertainty rather than the onset of a crash: the guide
reports a positive average 10-day forward S&P 500 return (~+1.2%) following
VVIX closes above 120. This is a contrarian mean-reversion signal distinct
from every VIX-level/VIX-term-structure strategy already tested in this repo
(those use ^VIX directly; this uses ^VVIX, the second-derivative "vol of
vol" measure).

Signal logic
------------
- Fetch ^VVIX (via load_equity, yfinance ticker) as the trigger series and
  the underlying equity (SPY/QQQ) as the tradable asset -- both loaded
  inside generate_signals/generate_returns via load_equity so the strategy
  is self-contained and matches the grid tester's
  generate_returns_fn(price_df, **params) contract (price_df is SPY/QQQ;
  VVIX is fetched internally aligned to the same date range).
- Long entry: ^VVIX closes above `vvix_extreme` (default 120).
- Exit: ^VVIX closes back below `vvix_exit` (default 100, i.e. reverting
  toward its long-run mean), or a max holding period of `max_hold_days`
  trading days is reached (avoid indefinite holds if VVIX stays elevated).
- Flat otherwise.

Interface contract for validators/grid-tester: generate_signals/
generate_returns accept price_df (the tradable asset's OHLCV, e.g. SPY) plus
keyword params, matching every other strategy in strategies/.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_vvix_aligned(index: pd.DatetimeIndex) -> pd.Series:
    """Fetch ^VVIX and align/reindex to the given (equity) index."""
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity  # noqa: E402

    start = index.min() - timedelta(days=10)
    end = index.max() + timedelta(days=2)
    vvix_df = load_equity("^VVIX", start.to_pydatetime() if hasattr(start, "to_pydatetime") else start,
                           end.to_pydatetime() if hasattr(end, "to_pydatetime") else end)
    vvix_df = _prep(vvix_df)
    vvix_close = vvix_df["close"]
    # Align to trading-asset index; forward-fill any gaps (e.g. holiday mismatches).
    aligned = vvix_close.reindex(index.union(vvix_close.index)).sort_index().ffill().reindex(index)
    return aligned


def generate_signals(
    price_df: pd.DataFrame,
    vvix_extreme: float = 120.0,
    vvix_exit: float = 100.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series for the equity in price_df."""
    df = _prep(price_df)
    close_index = df.index

    vvix = _load_vvix_aligned(close_index)

    entry = vvix > vvix_extreme
    exit_meanrev = vvix < vvix_exit

    position = pd.Series(0, index=close_index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close_index)):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or held >= max_hold_days:
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
    """Position-weighted daily returns of the tradable asset (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
