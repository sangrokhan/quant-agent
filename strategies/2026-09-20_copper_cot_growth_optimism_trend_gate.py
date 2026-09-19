"""Strategy: CFTC COT Copper Managed-Money net-position sign as
economic-growth-confirmation trend gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id 2026-09-20-044):
Eighth COT-based strategy this cron trigger, eighth distinct market
(Copper futures, COMEX/Disaggregated report -- first use of Copper COT
data in this repo; confirmed feasible via direct Socrata API call).
Per CME Group's own COT whitepaper ("Copper: A Leading Indicator for
Growth" -- "A net-short position points to negative economic
expectations, while a move to a net-long position suggests a shift
towards economic optimism") and MacroMicro/StoneX COT-education pages
read via browser_exec this iteration: copper is famously nicknamed
"Dr. Copper" for its correlation with global industrial demand/growth
expectations, and the SIGN of Managed Money speculators' net position
(not just its percentile extreme, a distinct technique from this
trigger's other COT strategies) is treated by CME's own materials as a
real-time growth-sentiment barometer. This strategy applies that as a
TREND-CONFIRMATION gate (same "and-gate" pattern as this trigger's
accepted Gold strategy -038, but using the raw SIGN of copper Managed
Money net position rather than its slope, and applied to CPER/copper
itself as the primary asset rather than gold): go long CPER only when
BOTH (1) close > SMA(trend_window) AND (2) Copper Managed Money net
position (long - short) is positive (net-long, i.e. "growth-optimistic"
per CME's framing) -- economic-growth positioning confirming the
copper price uptrend, distinct from a pure price-momentum signal alone.

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

_COT_ENDPOINT = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"
_COPPER_MARKET = "COPPER- #1 - COMMODITY EXCHANGE INC."


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return df


def _fetch_copper_mm_net() -> pd.Series:
    if _COPPER_MARKET in _cot_cache:
        return _cot_cache[_COPPER_MARKET]

    params = {
        "$where": f"market_and_exchange_names='{_COPPER_MARKET}'",
        "$select": "report_date_as_yyyy_mm_dd,m_money_positions_long_all,m_money_positions_short_all",
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
        _cot_cache[_COPPER_MARKET] = series
        return series

    idx = pd.to_datetime([r["report_date_as_yyyy_mm_dd"] for r in data], utc=True)
    net = pd.Series(
        [float(r["m_money_positions_long_all"]) - float(r["m_money_positions_short_all"]) for r in data],
        index=idx,
    ).sort_index()
    net = net[~net.index.duplicated(keep="last")]
    _cot_cache[_COPPER_MARKET] = net
    return net


def _growth_optimism_flag(
    price_index: pd.DatetimeIndex,
    report_lag_days: int,
) -> pd.Series:
    net = _fetch_copper_mm_net()
    if net.empty:
        return pd.Series(False, index=price_index)

    net_long = net > 0

    lagged_index = net_long.index + pd.Timedelta(days=report_lag_days)
    net_long_lagged = pd.Series(net_long.values, index=lagged_index)

    full_daily_idx = pd.date_range(
        min(price_index.min(), net_long_lagged.index.min()),
        max(price_index.max(), net_long_lagged.index.max()),
        freq="D",
        tz="UTC",
    )
    daily_signal = net_long_lagged.reindex(full_daily_idx).ffill().fillna(False)
    return daily_signal.reindex(price_index, method="ffill").fillna(False).astype(bool)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    report_lag_days: int = 3,
) -> pd.Series:
    """Long only when close > SMA(trend_window) AND Copper Managed Money net
    position is positive (net-long -- CME's own "growth optimism" framing
    confirming the uptrend)."""
    df = _prep(price_df)
    close = df["close"]
    trend_long = close > close.rolling(trend_window).mean()
    growth_optimistic = _growth_optimism_flag(df.index, report_lag_days)
    position = (trend_long.fillna(False) & growth_optimistic).astype(float)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    report_lag_days: int = 3,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, trend_window=trend_window, report_lag_days=report_lag_days)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
