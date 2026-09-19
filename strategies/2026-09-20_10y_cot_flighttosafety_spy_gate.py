"""Strategy: CFTC COT 10-Year Treasury futures leveraged-money extreme-long
("flight to safety") SPY defensive gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id 2026-09-20-046):
Tenth (final) COT-based strategy this cron trigger, ninth distinct market
(10-Year U.S. Treasury Note futures, CBOT -- first use of Treasury-futures
COT data in this repo; confirmed feasible: 817 weekly rows). Per
modigin.com's COT-education page ("10Y Treasury positioning provides
cleanest macro risk sentiment signal across all asset classes. Extreme
leveraged long 10Y combined with equity [weakness suggests risk-off
flight-to-safety]") and futuresbench.com/cotdata.net COT pages read via
browser_exec this iteration: when leveraged-money speculators build an
extreme net-long position in 10-Year Treasury futures (bond-buying =
yield-seeking safety trade), it signals broad risk-off positioning that
often precedes or coincides with equity weakness/stress. This strategy
uses that as a DEFENSIVE GATE on SPY (mirroring this cron trigger's
already-accepted VIX-futures-complacency defensive-gate pattern -040, but
using Treasury-futures positioning instead of VIX positioning as the
macro-risk signal): hold SPY (trend gate: close > SMA(trend_window))
UNLESS 10-Year Treasury futures leveraged-money net position is in the
top `high_pct` trailing percentile (extreme flight-to-safety
positioning), in which case go flat regardless of the equity trend.

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
_TY_MARKET = "10-YEAR U.S. TREASURY NOTES - CHICAGO BOARD OF TRADE"


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return df


def _fetch_ty_lev_money_net() -> pd.Series:
    if _TY_MARKET in _cot_cache:
        return _cot_cache[_TY_MARKET]

    params = {
        "$where": f"market_and_exchange_names='{_TY_MARKET}'",
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
        _cot_cache[_TY_MARKET] = series
        return series

    idx = pd.to_datetime([r["report_date_as_yyyy_mm_dd"] for r in data], utc=True)
    net = pd.Series(
        [float(r["lev_money_positions_long"]) - float(r["lev_money_positions_short"]) for r in data],
        index=idx,
    ).sort_index()
    net = net[~net.index.duplicated(keep="last")]
    _cot_cache[_TY_MARKET] = net
    return net


def _flight_to_safety_flag(
    price_index: pd.DatetimeIndex,
    lookback_weeks: int,
    high_pct: float,
    report_lag_days: int,
) -> pd.Series:
    net = _fetch_ty_lev_money_net()
    if net.empty:
        return pd.Series(False, index=price_index)

    pct_rank = net.rolling(lookback_weeks, min_periods=max(8, lookback_weeks // 4)).apply(
        lambda w: (w.rank(pct=True).iloc[-1]), raw=False
    )
    flight_to_safety = pct_rank >= high_pct

    lagged_index = flight_to_safety.index + pd.Timedelta(days=report_lag_days)
    flight_to_safety_lagged = pd.Series(flight_to_safety.values, index=lagged_index)

    full_daily_idx = pd.date_range(
        min(price_index.min(), flight_to_safety_lagged.index.min()),
        max(price_index.max(), flight_to_safety_lagged.index.max()),
        freq="D",
        tz="UTC",
    )
    daily_signal = flight_to_safety_lagged.reindex(full_daily_idx).ffill().fillna(False)
    return daily_signal.reindex(price_index, method="ffill").fillna(False).astype(bool)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 100,
    lookback_weeks: int = 156,
    high_pct: float = 0.90,
    report_lag_days: int = 3,
) -> pd.Series:
    """Long SPY when close > SMA(trend_window) UNLESS 10Y Treasury futures
    leveraged-money net position is in the top `high_pct` percentile of its
    trailing `lookback_weeks` distribution (extreme flight-to-safety
    positioning -> defensive flat)."""
    df = _prep(price_df)
    close = df["close"]
    trend_long = close > close.rolling(trend_window).mean()
    flight_to_safety = _flight_to_safety_flag(df.index, lookback_weeks, high_pct, report_lag_days)
    position = (trend_long.fillna(False) & ~flight_to_safety).astype(float)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 100,
    lookback_weeks: int = 156,
    high_pct: float = 0.90,
    report_lag_days: int = 3,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df, trend_window=trend_window, lookback_weeks=lookback_weeks,
        high_pct=high_pct, report_lag_days=report_lag_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
