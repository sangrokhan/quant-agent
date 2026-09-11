"""Strategy: Long SVXY (short-vol ETF) gated by the VIX/VIX3M term-structure
contango regime.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-071):
Per backtesteverything.com's "Backtesting the VIX Term Structure: Trading
Volatility ETFs Systematically" (visited this iteration), the VIX futures
term structure is in contango ~80% of the time (short-dated VIX cheaper than
longer-dated), during which long-volatility products structurally decay as
they roll into more expensive contracts -- the source's own primary trade is
"short VXX (or buy SVXY) during contango and go flat or long VXX during
backwardation", using the VIX/VIX3M ratio exceeding 1.0 as the backwardation
(flip to flat) signal. This repo already tested several VIX/VIX3M
term-structure strategies (2026-09-04-157, 2026-09-05-028, 2026-09-06-127,
2026-09-10-038/-042/-121) but ALL of them applied the term-structure signal
as a regime GATE on top of trading QQQ/SPY/BTC/ETH price action. This is the
first strategy in this repo to trade the actual volatility product (SVXY)
itself directly -- i.e. the term-structure signal isn't a side-filter on an
unrelated asset, it IS the asset being harvested, which is the source's
literal trade construction, not an equity-market proxy for it.

Signal logic
------------
- Ratio = VIX close / VIX3M close (loaded internally via data/loaders.py,
  independent of whatever price_df is passed in -- but generate_returns
  applies the resulting position to price_df's own close-to-close returns,
  so this strategy is intended to be run with SVXY as the input symbol).
- Long (1) when ratio <= contango_thresh (contango / calm regime).
- Flat (0) when ratio > contango_thresh (backwardation / acute stress,
  the source's explicit "catastrophic if held through backwardation"
  warning -- e.g. Feb 2018 Volmageddon, Mar 2020 COVID crash).
- min_hold_days: once flat due to a backwardation flip, require the ratio
  to stay in contango for at least this many additional days before
  re-entering (source notes backwardation episodes are often followed by
  a choppy transition back to contango; this reduces whipsaw switching).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} long/flat)
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_vix_ratio(index: pd.DatetimeIndex) -> pd.Series:
    """Load ^VIX and ^VIX3M via data/loaders.py, compute ratio aligned to index."""
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity  # noqa: E402

    start = (index.min() - pd.Timedelta(days=10)).to_pydatetime()
    end = (index.max() + pd.Timedelta(days=10)).to_pydatetime()

    vix = load_equity("^VIX", start, end)
    vix3m = load_equity("^VIX3M", start, end)

    vix = vix.set_index("timestamp")["close"] if "timestamp" in vix.columns else vix["close"]
    vix3m = vix3m.set_index("timestamp")["close"] if "timestamp" in vix3m.columns else vix3m["close"]

    vix.index = pd.to_datetime(vix.index).tz_localize(None)
    vix3m.index = pd.to_datetime(vix3m.index).tz_localize(None)

    ratio = (vix / vix3m).dropna()
    ratio = ratio.reindex(pd.to_datetime(index).tz_localize(None)).ffill()
    ratio.index = index
    return ratio


def generate_signals(
    price_df: pd.DataFrame,
    contango_thresh: float = 1.0,
    min_hold_days: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series for SVXY."""
    df = _prep(price_df)
    close = df["close"]

    ratio = _load_vix_ratio(close.index)
    contango = (ratio <= contango_thresh).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    days_in_contango_since_flip = 0
    for i in range(len(close)):
        is_contango = bool(contango.iloc[i])
        if in_position:
            if not is_contango:
                in_position = False
                days_in_contango_since_flip = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if is_contango:
                days_in_contango_since_flip += 1
            else:
                days_in_contango_since_flip = 0
            if days_in_contango_since_flip >= min_hold_days:
                in_position = True
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
