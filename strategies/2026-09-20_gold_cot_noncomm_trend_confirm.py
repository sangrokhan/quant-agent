"""Strategy: CFTC COT Gold futures non-commercial net-position TREND-CONFIRMATION gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id 2026-09-20-038):
Second COT-based strategy in this repo this cron trigger (first was
2026-09-20-037, a Bitcoin leveraged-money EXTREME-percentile CONTRARIAN
fade on CME Bitcoin futures -- rejected). This iteration deliberately
tests the OPPOSITE economic framing (mirroring this cron trigger's own
funding-rate contrarian-vs-trend-confirmation pair, ids 2026-09-20-031 /
2026-09-20-035) on a DIFFERENT market: COMEX Gold futures "non-commercial"
(large speculator) net position (long - short), the CFTC's own
"Legacy"-format speculator-equivalent classification (per CFTC.gov COT
documentation and TradingView/Coinfuty/AlphaX open-interest-trend-
confirmation education pages read via browser_exec this iteration: "a
breakout accompanied by rising open interest/positioning carries more
weight than one on falling positioning, because new capital confirms
conviction"). Concretely: go long GLD only when BOTH (1) close >
SMA(trend_window) (standard uptrend gate, this repo's convention) AND (2)
the non-commercial net position's rolling `positioning_window`-week SLOPE
is positive (speculators have been building, not unwinding, their net-long
book -- confirming genuine conviction behind the price trend, not just
price momentum in isolation). This is the FIRST use of Gold futures COT
data and the FIRST GLD-price strategy gated by an on-exchange-derivatives
positioning signal in this repo.

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

_COT_ENDPOINT = "https://publicreporting.cftc.gov/resource/jun7-fc8e.json"
_GOLD_MARKET = "GOLD - COMMODITY EXCHANGE INC."


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return df


def _fetch_gold_noncomm_net() -> pd.Series:
    if _GOLD_MARKET in _cot_cache:
        return _cot_cache[_GOLD_MARKET]

    params = {
        "$where": f"market_and_exchange_names='{_GOLD_MARKET}'",
        "$select": "report_date_as_yyyy_mm_dd,noncomm_positions_long_all,noncomm_positions_short_all",
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
        _cot_cache[_GOLD_MARKET] = series
        return series

    idx = pd.to_datetime([r["report_date_as_yyyy_mm_dd"] for r in data], utc=True)
    net = pd.Series(
        [float(r["noncomm_positions_long_all"]) - float(r["noncomm_positions_short_all"]) for r in data],
        index=idx,
    ).sort_index()
    net = net[~net.index.duplicated(keep="last")]
    _cot_cache[_GOLD_MARKET] = net
    return net


def _positioning_confirms(
    price_index: pd.DatetimeIndex,
    positioning_window: int,
    report_lag_days: int,
) -> pd.Series:
    net = _fetch_gold_noncomm_net()
    if net.empty:
        return pd.Series(False, index=price_index)

    slope = net.diff(positioning_window)
    confirms = slope > 0

    lagged_index = confirms.index + pd.Timedelta(days=report_lag_days)
    confirms_lagged = pd.Series(confirms.values, index=lagged_index)

    full_daily_idx = pd.date_range(
        min(price_index.min(), confirms_lagged.index.min()),
        max(price_index.max(), confirms_lagged.index.max()),
        freq="D",
        tz="UTC",
    )
    daily_signal = confirms_lagged.reindex(full_daily_idx).ffill().fillna(False)
    return daily_signal.reindex(price_index, method="ffill").fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    positioning_window: int = 8,
    report_lag_days: int = 3,
) -> pd.Series:
    """Long only when close > SMA(trend_window) AND Gold futures
    non-commercial net position has risen over the trailing
    `positioning_window` COT weeks (speculator conviction confirming trend)."""
    df = _prep(price_df)
    close = df["close"]
    trend_long = close > close.rolling(trend_window).mean()
    confirms = _positioning_confirms(df.index, positioning_window, report_lag_days)
    position = (trend_long.fillna(False) & confirms).astype(float)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    positioning_window: int = 8,
    report_lag_days: int = 3,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df, trend_window=trend_window, positioning_window=positioning_window,
        report_lag_days=report_lag_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
