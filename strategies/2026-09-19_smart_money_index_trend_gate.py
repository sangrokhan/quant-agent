"""Strategy: Smart Money Index (SMI) trend-confirmation gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-19-057):
Per Grokipedia's "Smart Money Index" page
(https://grokipedia.com/page/Smart_money_index), the Smart Money Index
(SMI, Lynn Elgert 1988 / Don Hays 1990s) is a cumulative price-based
sentiment index: Today's SMI = Yesterday's SMI - (gain/loss in the first
30 minutes of trading) + (gain/loss in the last hour of trading). The
underlying theory: retail ("dumb money") activity concentrates near the
open, institutional ("smart money") activity concentrates near the close,
so subtracting the opening move and adding the closing move isolates a
cumulative measure of "informed" flow. A rising SMI alongside rising
price is bullish confirmation; SMI diverging from price (e.g. price makes
a new high but SMI does not) is a bearish warning.

We adapt this into a trend-confirmation gate (the same construction
pattern already validated repeatedly in this repo for other
regime/confirmation ratios, e.g. XSD/SMH breadth gate 2026-09-19-012,
SPHB/SPLV rotation gate 2026-09-20-049): stay long the primary asset only
while (a) its own price is in an uptrend (close > SMA(trend_window)) AND
(b) the SMI itself is also rising (SMI > its own trailing SMA(smi_window),
i.e. "smart money" confirms the uptrend rather than diverging from it).
Because 30-minute bars are capped by yfinance to ~60 days of history
(same constraint documented in 2026-09-19-054), we adapt to 1-HOUR bars:
"first hour" replaces "first 30 minutes", matching the same first/last-bar
asymmetry the source describes, over data/loaders.py's ~2-year 1h history
window. This is a genuinely distinct construction from 2026-09-19-054
(this same cron trigger's first-hour/last-hour SIGN-PREDICTION strategy,
which trades the SAME DAY's last-hour return conditioned on that day's own
first-hour sign) -- SMI is a CUMULATIVE running index across ALL days,
used here as a multi-day trend-confirmation filter, not a same-day
directional bet. Also distinct from the already-tested Fosback/Dysart
Negative Volume Index (2026-09-04-139/2026-09-14-131), which is
volume-based rather than intraday-timing-based.

Signal logic
------------
- Fetch 1h bars for the primary symbol (own hourly OHLCV, not price_df's
  granularity -- price_df's own daily dates set the output date range).
- Per trading day: first_hour_ret = (first bar close - first bar open) /
  first bar open; last_hour_ret = (last bar close - last bar open) / last
  bar open.
- SMI[day] = SMI[day-1] - first_hour_ret[day] + last_hour_ret[day]
  (cumulative, starts at 0).
- smi_sma = SMA(SMI, smi_window).
- smi_confirms = SMI > smi_sma (smart-money-driven cumulative index
  itself trending up).
- trend_up = close(primary) > SMA(close(primary), trend_window).
- Long (position=1) when trend_up AND smi_confirms; flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
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


def _daily_smi(symbol: str, asset_class: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    hourly = _get_hourly(symbol, asset_class, start, end)
    if hourly.empty:
        return pd.Series(dtype=float)

    increments = {}
    for date, group in hourly.groupby("date"):
        group = group.sort_values("timestamp")
        if len(group) < 2:
            continue
        first_bar = group.iloc[0]
        last_bar = group.iloc[-1]
        if first_bar["open"] == 0 or last_bar["open"] == 0:
            continue
        first_hour_ret = (first_bar["close"] - first_bar["open"]) / first_bar["open"]
        last_hour_ret = (last_bar["close"] - last_bar["open"]) / last_bar["open"]
        increments[pd.Timestamp(date, tz="UTC")] = -first_hour_ret + last_hour_ret

    increments_series = pd.Series(increments).sort_index()
    return increments_series.cumsum()


def generate_signals(
    price_df: pd.DataFrame,
    symbol: str = "SPY",
    asset_class: str = "equity",
    trend_window: int = 100,
    smi_window: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    idx = df.index

    sma = close.rolling(trend_window).mean()
    trend_up = (close > sma).fillna(False)

    smi = _daily_smi(symbol, asset_class, idx.min(), idx.max())
    if smi.empty:
        return pd.Series(0, index=idx, dtype=int)

    smi_aligned = smi.reindex(idx.normalize()).ffill()
    smi_aligned.index = idx
    smi_sma = smi_aligned.rolling(smi_window, min_periods=max(2, smi_window // 2)).mean()
    smi_confirms = (smi_aligned > smi_sma).fillna(False)

    position = (trend_up & smi_confirms).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    symbol: str = "SPY",
    asset_class: str = "equity",
    trend_window: int = 100,
    smi_window: int = 20,
) -> pd.Series:
    """Return the strategy's daily return series."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        symbol=symbol,
        asset_class=asset_class,
        trend_window=trend_window,
        smi_window=smi_window,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
