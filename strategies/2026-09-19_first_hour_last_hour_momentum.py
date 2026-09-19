"""Strategy: Intraday first-hour/last-hour momentum (Gao, Han, Li & Zhou 2017).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-19-054):
Per Gao, Han, Li & Zhou (2017) "Market Intraday Momentum" (as recreated by
QuantConnect's "Intraday ETF Momentum" tutorial,
https://www.quantconnect.com/research/15348/intraday-etf-momentum/), the
sign of an ETF's FIRST half-hour return predicts the sign of its LAST
half-hour return, driven by late-informed/close-preferring traders whose
trading pushes the close in the same direction as the informed morning
move. The original paper's disclosed backtest averaged 6.67%/yr (SPY),
11.72%/yr (IWM), 24.22%/yr (IYR).

Adapted to 1-HOUR bars (rather than the paper's 30-minute bars): FIRST
HOUR return sign predicts LAST HOUR return sign. This adaptation is
necessary because data/loaders.py's yfinance interval="30m" is capped by
the yfinance API to the trailing ~60 days, while interval="1h" covers
~2 years of history -- enough for a meaningful backtest. This is a
genuinely distinct construction from every existing strategy in this repo
(none use intraday first/last-hour sign-prediction; the closest,
2026-09-05-071/2026-09-14-100's Intraday Momentum Index, is Chande's
open-to-close-body RSI-analog oscillator, unrelated to this first-half-vs-
last-half sign-prediction mechanism).

Because this needs genuine intraday (sub-daily) bars, the strategy
fetches its OWN hourly OHLCV internally via data/loaders.py (ignoring the
`price_df` argument's granularity/symbol -- the interface contract still
accepts a `price_df` positional arg per Step 5's required signature, but
this strategy uses it only to determine the backtest's start/end date
range; the actual bars used are separately fetched at 1h resolution for
the ticker given by the `symbol` parameter). The daily return series
returned aligns to CALENDAR DATES (last-hour session-close return per
day, zero on days with insufficient intraday bars), so it is compatible
with validation/grid_test.py's vol-regime masking (which slices on the
DAILY closes of whatever `price_df` was supplied).

Signal logic
------------
- Group the fetched 1h bars by trading day.
- `morning_ret` = (first hour's close - first hour's open) / first hour's
  open.
- `last_hour_ret` = (last hour's close - last hour's open) / last hour's
  open.
- If `morning_ret > threshold`: go long for the last hour (day's strategy
  return = +last_hour_ret).
- If `morning_ret < -threshold`: go short for the last hour (day's
  strategy return = -last_hour_ret).
- Otherwise flat (day's strategy return = 0).
- Days with fewer than 2 hourly bars are skipped (return 0).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (position sign per
        day, -1/0/1, NOT restricted to {0,1} since this is a long/short
        strategy -- documented deviation from the usual {0,1} contract,
        consistent with other repo strategies that use signed positions
        when the hypothesis is inherently long/short, e.g. hysteresis-band
        z-score strategies).
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity, load_crypto  # noqa: E402

_hourly_cache: dict = {}


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def _get_hourly(symbol: str, asset_class: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    key = (symbol, asset_class, start.date().isoformat(), end.date().isoformat())
    if key in _hourly_cache:
        return _hourly_cache[key]

    # yfinance's 1h interval is capped at ~730 days of history -- clamp the
    # fetch window so we don't request further back than that (older dates
    # simply return no signal, handled by the empty-day skip below).
    max_lookback = timedelta(days=729)
    fetch_start = max(start.to_pydatetime().replace(tzinfo=None), datetime.utcnow() - max_lookback)
    fetch_end = end.to_pydatetime().replace(tzinfo=None)

    if asset_class == "equity":
        df = load_equity(symbol, fetch_start, fetch_end, interval="1h")
    else:
        df = load_crypto(symbol, fetch_start, fetch_end, interval="1h")

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["date"] = df["timestamp"].dt.date
    _hourly_cache[key] = df
    return df


def _daily_strategy_returns(
    symbol: str,
    asset_class: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    threshold: float,
) -> pd.Series:
    hourly = _get_hourly(symbol, asset_class, start, end)
    if hourly.empty:
        return pd.Series(dtype=float)

    daily_returns = {}
    for date, group in hourly.groupby("date"):
        group = group.sort_values("timestamp")
        if len(group) < 2:
            continue
        first_bar = group.iloc[0]
        last_bar = group.iloc[-1]
        if first_bar["open"] == 0 or last_bar["open"] == 0:
            continue
        morning_ret = (first_bar["close"] - first_bar["open"]) / first_bar["open"]
        last_hour_ret = (last_bar["close"] - last_bar["open"]) / last_bar["open"]

        if morning_ret > threshold:
            day_ret = last_hour_ret
        elif morning_ret < -threshold:
            day_ret = -last_hour_ret
        else:
            day_ret = 0.0
        daily_returns[pd.Timestamp(date, tz="UTC")] = day_ret

    return pd.Series(daily_returns).sort_index()


def generate_signals(
    price_df: pd.DataFrame,
    symbol: str = "SPY",
    asset_class: str = "equity",
    threshold: float = 0.0,
) -> pd.Series:
    """Return a {-1,0,1} position-sign series aligned to price_df's daily dates."""
    df = _prep(price_df)
    idx = df.index

    hourly = _get_hourly(symbol, asset_class, idx.min(), idx.max())
    if hourly.empty:
        return pd.Series(0, index=idx, dtype=int)

    signs = {}
    for date, group in hourly.groupby("date"):
        group = group.sort_values("timestamp")
        if len(group) < 2:
            continue
        first_bar = group.iloc[0]
        if first_bar["open"] == 0:
            continue
        morning_ret = (first_bar["close"] - first_bar["open"]) / first_bar["open"]
        if morning_ret > threshold:
            signs[pd.Timestamp(date, tz="UTC")] = 1
        elif morning_ret < -threshold:
            signs[pd.Timestamp(date, tz="UTC")] = -1
        else:
            signs[pd.Timestamp(date, tz="UTC")] = 0

    sign_series = pd.Series(signs).sort_index()
    return sign_series.reindex(idx.normalize()).fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    symbol: str = "SPY",
    asset_class: str = "equity",
    threshold: float = 0.0,
) -> pd.Series:
    """Return the strategy's daily return series (last-hour return, signed by morning momentum)."""
    df = _prep(price_df)
    idx = df.index

    daily_ret = _daily_strategy_returns(symbol, asset_class, idx.min(), idx.max(), threshold)
    if daily_ret.empty:
        return pd.Series(0.0, index=idx)

    # Align to price_df's own daily dates (normalize to midnight UTC) so
    # grid_test.py's vol-regime masking (built on price_df's own daily
    # closes) can slice this return series consistently.
    aligned = daily_ret.reindex(idx.normalize()).fillna(0.0)
    aligned.index = idx
    return aligned
