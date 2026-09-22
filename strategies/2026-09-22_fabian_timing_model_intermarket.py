"""Strategy: Fabian Timing Model -- 39-week intermarket SMA trend regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl, this iteration's id):
Per QuantifiedStrategies.com's "Fabian Market Timing Model" article
(https://www.quantifiedstrategies.com/fabian-timing-model/, Richard Fabian,
1960s -- "The mutual fund wealth builder"), a weekly trend-following regime
filter that requires THREE broad-market indices to agree reduces false
signals versus a single-index trend filter: buy/hold SPY when the S&P 500,
Dow Jones Industrial Average, and the Utilities sector are ALL trading above
their own 39-week (~195 trading day) simple moving average; sell/go flat
when 2 or more of the three drop below their respective 39-week MA. The
source's own disclosed free rule (the underlying Python backtest code is
members-only, but the buy/sell condition itself and its rationale -- fewer
false signals from cross-confirmation across 3 correlated-but-distinct market
segments -- are fully disclosed).

We proxy the three indices with liquid, long-history ETFs fetchable via
data/loaders.py's yfinance wrapper: SPY (S&P 500), DIA (Dow Jones Industrial
Average), XLU (Utilities Select Sector). The traded asset in generate_returns
is always the primary price_df passed in (so the grid test can apply this to
QQQ/SPY and, for the infeasibility check, crypto too), with the intermarket
39-week-MA rule computed from SPY+DIA+XLU regardless of what's traded.

Distinct from all prior single-index SMA-crossover trend filters in this
repo (e.g. 2026-09-03_momentum_trend200_filter.py) and from the SPY/TLT
stock-vs-bond ratio regime filter (2026-09-05_spy_tlt_ratio_regime.py) via
its 3-way intermarket voting/confirmation structure (majority-of-3, not a
simple crossover) applied at weekly (not daily) granularity.

Signal logic
------------
- Resample SPY, DIA, XLU closes to weekly (Friday) frequency.
- Compute each index's own 39-week SMA.
- "Above" count = number of {SPY, DIA, XLU} currently trading above their
  own 39-week SMA (0-3).
- BUY (go long) when above_count == 3 (all three above their MA).
- SELL (go flat) when above_count <= sell_threshold (default: <=1, i.e. 2
  or more are below their MA -- source's own stated rule).
- Otherwise (above_count == 2, in the source's example that's a "hold your
  existing position" zone -- we implement this as no-change/persist prior
  state, matching the source's "sell if two or more break down" framing,
  which implies staying long through a single break).
- The resulting weekly regime signal is forward-filled onto the daily
  price_df index of whatever asset is being traded.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity  # noqa: E402

_regime_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def _weekly_above_ma(close: pd.Series, ma_weeks: int) -> pd.Series:
    weekly = close.resample("W-FRI").last().dropna()
    sma = weekly.rolling(ma_weeks, min_periods=ma_weeks).mean()
    return (weekly > sma).astype(float)  # NaN-safe float, 1.0/0.0/NaN


def _get_regime(start: pd.Timestamp, end: pd.Timestamp, ma_weeks: int) -> pd.Series:
    """Weekly regime position series {0,1} from SPY/DIA/XLU 39wk-MA voting, cached."""
    key = (start.date().isoformat(), end.date().isoformat(), ma_weeks)
    if key in _regime_cache:
        return _regime_cache[key]

    fetch_start = datetime(max(start.year - 3, 2000), 1, 1, tzinfo=timezone.utc)
    fetch_end = datetime(end.year + 1, 1, 1, tzinfo=timezone.utc)

    closes = {}
    for sym in ("SPY", "DIA", "XLU"):
        df = load_equity(sym, fetch_start, fetch_end)
        s = df.set_index(pd.to_datetime(df["timestamp"], utc=True))["close"]
        s = s[~s.index.duplicated(keep="first")].sort_index()
        closes[sym] = s

    above = pd.DataFrame({sym: _weekly_above_ma(s, ma_weeks) for sym, s in closes.items()})
    above = above.dropna(how="any")
    above_count = above.sum(axis=1)

    position = pd.Series(0, index=above_count.index, dtype=int)
    in_position = False
    for ts, cnt in above_count.items():
        if cnt == 3:
            in_position = True
        elif cnt <= 1:
            in_position = False
        # cnt == 2: persist prior state (source's "hold" zone)
        position.loc[ts] = int(in_position)

    _regime_cache[key] = position
    return position


def generate_signals(
    price_df: pd.DataFrame,
    ma_weeks: int = 39,
) -> pd.Series:
    """Return a {0,1} long/flat position series from the Fabian intermarket regime."""
    df = _prep(price_df)
    idx = df.index

    weekly_position = _get_regime(idx.min(), idx.max(), ma_weeks)
    # Forward-fill the weekly regime signal onto the daily index.
    position = weekly_position.reindex(idx, method="ffill").fillna(0).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
