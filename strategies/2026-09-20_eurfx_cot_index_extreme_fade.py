"""Strategy: CFTC COT Euro FX "COT Index" (1-year min-max normalization)
extreme contrarian fade.

Hypothesis (see knowledge_base/strategies_log.jsonl id 2026-09-20-043):
Seventh COT-based strategy this cron trigger, seventh distinct market
(Euro FX futures, CME -- first use of currency-futures COT data in this
repo; confirmed feasible: 1058 weekly rows since 2006). Also the FIRST
use of the specific "COT Index" NORMALIZATION TECHNIQUE distinct from the
raw-percentile-rank-over-3-years method used in this cron trigger's
earlier COT strategies (-037, -039, -041, -042): per FXNX.com's COT
education page ("When the COT Index for Non-Commercials hits 90% or
higher, it means speculators are as bullish as they've been in a year")
and CME Group's own "The CFTC COT Report: Trade FX Futures More
Effectively" article, the widely-used "COT Index" formula is a min-max
normalization over a TRAILING 1-YEAR (52-week) window specifically (not
3 years): COT_Index = (net_position - min(net_position, 52wk)) /
(max(net_position, 52wk) - min(net_position, 52wk)) * 100. This produces
a 0-100 scale distinct from percentile rank (percentile rank counts how
many historical weeks are below the current value; min-max normalization
measures where the current value sits between the extremes, which is
more sensitive to a single historical outlier week). Applied here as a
contrarian fade on EUR/USD (proxied by FXE): go long when the 1-year COT
Index for non-commercial (speculator) net EUR FX position is <= low_idx
(speculators near-least-bullish of the past year -> contrarian long), flat
otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

import pandas as pd

_cot_cache: dict = {}

_COT_ENDPOINT = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"
_EUR_MARKET = "EURO FX - CHICAGO MERCANTILE EXCHANGE"


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return df


def _fetch_eur_noncomm_net() -> pd.Series:
    if _EUR_MARKET in _cot_cache:
        return _cot_cache[_EUR_MARKET]

    params = {
        "$where": f"market_and_exchange_names='{_EUR_MARKET}'",
        "$select": "report_date_as_yyyy_mm_dd,lev_money_positions_long,lev_money_positions_short",
        "$order": "report_date_as_yyyy_mm_dd ASC",
        "$limit": "5000",
    }
    url = _COT_ENDPOINT + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        data = []

    if not data:
        series = pd.Series(dtype=float)
        _cot_cache[_EUR_MARKET] = series
        return series

    idx = pd.to_datetime([r["report_date_as_yyyy_mm_dd"] for r in data], utc=True)
    net = pd.Series(
        [float(r["lev_money_positions_long"]) - float(r["lev_money_positions_short"]) for r in data],
        index=idx,
    ).sort_index()
    net = net[~net.index.duplicated(keep="last")]
    _cot_cache[_EUR_MARKET] = net
    return net


def _cot_index_extreme_low(
    price_index: pd.DatetimeIndex,
    window_weeks: int,
    low_idx: float,
    report_lag_days: int,
) -> pd.Series:
    net = _fetch_eur_noncomm_net()
    if net.empty:
        return pd.Series(False, index=price_index)

    roll_min = net.rolling(window_weeks, min_periods=max(8, window_weeks // 4)).min()
    roll_max = net.rolling(window_weeks, min_periods=max(8, window_weeks // 4)).max()
    denom = (roll_max - roll_min).replace(0, pd.NA)
    cot_index = ((net - roll_min) / denom) * 100.0
    fade_long = cot_index <= low_idx

    lagged_index = fade_long.index + pd.Timedelta(days=report_lag_days)
    fade_long_lagged = pd.Series(fade_long.values, index=lagged_index)

    full_daily_idx = pd.date_range(
        min(price_index.min(), fade_long_lagged.index.min()),
        max(price_index.max(), fade_long_lagged.index.max()),
        freq="D",
        tz="UTC",
    )
    daily_signal = fade_long_lagged.reindex(full_daily_idx).ffill().fillna(False)
    return daily_signal.reindex(price_index, method="ffill").fillna(False).astype(bool)


def generate_signals(
    price_df: pd.DataFrame,
    window_weeks: int = 52,
    low_idx: float = 20.0,
    report_lag_days: int = 3,
) -> pd.Series:
    """Long only when the 1-year min-max "COT Index" for Euro FX
    leveraged-money net position is <= `low_idx` (near-least-bullish of the
    past year -> contrarian long), flat otherwise."""
    df = _prep(price_df)
    signal = _cot_index_extreme_low(df.index, window_weeks, low_idx, report_lag_days)
    return signal.astype(float)


def generate_returns(
    price_df: pd.DataFrame,
    window_weeks: int = 52,
    low_idx: float = 20.0,
    report_lag_days: int = 3,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df, window_weeks=window_weeks, low_idx=low_idx, report_lag_days=report_lag_days
    )
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
