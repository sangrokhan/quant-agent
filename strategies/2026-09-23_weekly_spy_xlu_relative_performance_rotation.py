"""Strategy: Weekly SPY vs XLU relative-performance rotation (rotate INTO the
stronger asset every week, always fully invested in one of the two).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-23-... this
iteration): Per QuantifiedStrategies.com's "Weekly Rotating System Between
S&P 500 And Utilities (SPY And XLU)" (disclosed summary read via
browser_exec Google SERP snippets this iteration -- the direct article URL
404'd and the Substack mirror slug could not be located, but the source's
own snippet is explicit and consistent across multiple independent SERP
hits: "The strategy consists of a weekly rotation system between the SPY
and XLU based on the past performance of each one"): each week, hold
whichever of SPY or XLU had the better trailing lookback-period return,
rotating the FULL position into the stronger asset rather than merely going
to cash/flat. This is economically distinct from every prior XLU/SPY-family
strategy in this repo: 2026-09-05-067 (XLU/SPY ratio 4-week ROC as a
binary risk-on/flat GATE on the underlying -- goes to CASH when XLU
outperforms, never holds XLU itself), 2026-09-17-068 (XLK/XLU SMA-crossover
regime gate, also flat-vs-invested, different pair), and 2026-09-20-089
(XLI/XLU ROC gate on trend-following entries, also flat-vs-invested).
This is the first strategy in this repo that ROTATES BETWEEN TWO ASSETS
(never goes to cash) based on relative trailing performance.

Daily-bar adaptation notes: the source's own cadence is weekly
(rebalance once per week); this repo's data/loaders.py provides daily
OHLCV, so the rotation decision is re-evaluated every `rebalance_days`
trading days (default 5, approximating one trading week) rather than on a
literal calendar-week boundary, holding the winner's position between
rebalances.

Signal logic
------------
- At each rebalance point (every rebalance_days bars), compute each asset's
  trailing lookback_days total return (SPY-analog underlying passed in as
  price_df, vs XLU fetched internally via data/loaders.py).
- Hold the underlying (price_df's own asset) if its trailing return >= XLU's
  trailing return; otherwise hold XLU, until the next rebalance point.
- Always fully invested in one of the two (no cash position), matching the
  source's own rotation (not risk-on/risk-off) framing.

Interface contract for validators/grid_test (see RESEARCH_LOOP.md Step 5/6):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position on the
        UNDERLYING (price_df's own asset); 1 = hold underlying, 0 = hold XLU
        instead)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns -- underlying's return while position==1, XLU's return
        while position==0)
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


def _load_xlu(start, end) -> pd.Series:
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity  # noqa: E402

    xlu_df = load_equity("XLU", start, end)
    xlu_df = xlu_df.set_index("timestamp") if "timestamp" in xlu_df.columns else xlu_df
    return xlu_df.sort_index()["close"]


def generate_signals(
    price_df: pd.DataFrame,
    lookback_days: int = 20,
    rebalance_days: int = 5,
) -> pd.Series:
    """Return a {0,1} series: 1 = hold underlying (price_df's own asset),
    0 = hold XLU instead. Rotation decision refreshed every rebalance_days
    bars, based on trailing lookback_days total return comparison."""
    df = _prep(price_df)
    close = df["close"]

    start = close.index.min()
    end = close.index.max()
    xlu_close = _load_xlu(start, end)
    xlu_close = xlu_close.reindex(close.index).ffill().bfill()

    underlying_trailing_ret = close.pct_change(periods=lookback_days)
    xlu_trailing_ret = xlu_close.pct_change(periods=lookback_days)

    hold_underlying = (underlying_trailing_ret >= xlu_trailing_ret).fillna(True)

    n = len(df)
    hold_arr = hold_underlying.to_numpy()
    pos = np.zeros(n, dtype=int)
    current = 1  # default to holding underlying until first valid comparison
    for i in range(n):
        if i % rebalance_days == 0:
            current = 1 if hold_arr[i] else 0
        pos[i] = current

    return pd.Series(pos, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    lookback_days: int = 20,
    rebalance_days: int = 5,
) -> pd.Series:
    """Daily strategy returns: underlying's return while position==1, XLU's
    return while position==0 (always fully invested in one of the two)."""
    df = _prep(price_df)
    close = df["close"]

    start = close.index.min()
    end = close.index.max()
    xlu_close = _load_xlu(start, end)
    xlu_close = xlu_close.reindex(close.index).ffill().bfill()

    position = generate_signals(price_df, lookback_days=lookback_days, rebalance_days=rebalance_days)
    underlying_daily_ret = close.pct_change().fillna(0.0)
    xlu_daily_ret = xlu_close.pct_change().fillna(0.0)

    # Position is based on which asset to hold TODAY (decided using data up
    # to and including yesterday's rebalance point) -- shift by 1 to avoid
    # lookahead, consistent with this repo's convention.
    pos_shifted = position.shift(1).fillna(1).astype(int)
    strat_ret = np.where(pos_shifted == 1, underlying_daily_ret, xlu_daily_ret)
    return pd.Series(strat_ret, index=df.index)
