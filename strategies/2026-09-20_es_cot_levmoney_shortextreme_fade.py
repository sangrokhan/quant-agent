"""Strategy: CFTC COT E-mini S&P 500 leveraged-money extreme-net-short
contrarian fade.

Hypothesis (see knowledge_base/strategies_log.jsonl id 2026-09-20-041):
Fifth COT-based strategy this cron trigger, fifth distinct market
(E-mini S&P 500 futures, CME -- first use of equity-index-futures COT
data in this repo; confirmed feasible via direct Socrata API call: 241
weekly rows, 2022-02 to present -- shorter history than other COT
markets tried this trigger, since CFTC only reports E-mini S&P 500 in the
newer TFF/Financial-futures classification from that date). Per
CMEGroup's own COT whitepaper ("E-mini S&P's the Ultimate Index?" --
"frequently recurring extremes on the chart of the weekly COT positioning
for the E-Mini S&P 500... [are historically notable turning points]")
and modigin.com/thetrading.tools COT-education pages read via
browser_exec this iteration: leveraged-money (hedge-fund-style
speculators, distinct from the asset-manager category which runs
structurally net-long) in E-mini S&P 500 futures run a persistently
net-SHORT book (hedging/spec shorting), and when that net-short reaches
an extreme (bottom `low_pct` percentile of its own trailing
`lookback_weeks` distribution -- i.e. MORE short than usual), it signals
maximal bearish positioning crowding with few incremental sellers left --
a contrarian bullish tell, mirroring the classic COT-extreme-fade logic
already applied to Bitcoin futures (-037, rejected) but on a completely
different underlying (equity index futures) and category (leveraged-money,
not the Bitcoin market's leveraged-money too, but here specifically SPY
rather than BTC).

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
_ES_MARKET = "E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE"


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return df


def _fetch_es_lev_money_net() -> pd.Series:
    if _ES_MARKET in _cot_cache:
        return _cot_cache[_ES_MARKET]

    params = {
        "$where": f"market_and_exchange_names='{_ES_MARKET}'",
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
        _cot_cache[_ES_MARKET] = series
        return series

    idx = pd.to_datetime([r["report_date_as_yyyy_mm_dd"] for r in data], utc=True)
    net = pd.Series(
        [float(r["lev_money_positions_long"]) - float(r["lev_money_positions_short"]) for r in data],
        index=idx,
    ).sort_index()
    net = net[~net.index.duplicated(keep="last")]
    _cot_cache[_ES_MARKET] = net
    return net


def _extreme_short_fade_signal(
    price_index: pd.DatetimeIndex,
    lookback_weeks: int,
    low_pct: float,
    report_lag_days: int,
) -> pd.Series:
    net = _fetch_es_lev_money_net()
    if net.empty:
        return pd.Series(False, index=price_index)

    pct_rank = net.rolling(lookback_weeks, min_periods=max(8, lookback_weeks // 4)).apply(
        lambda w: (w.rank(pct=True).iloc[-1]), raw=False
    )
    fade_long = pct_rank <= low_pct

    lagged_index = fade_long.index + pd.Timedelta(days=report_lag_days)
    fade_long_lagged = pd.Series(fade_long.values, index=lagged_index)

    full_daily_idx = pd.date_range(
        min(price_index.min(), fade_long_lagged.index.min()),
        max(price_index.max(), fade_long_lagged.index.max()),
        freq="D",
        tz="UTC",
    )
    daily_signal = fade_long_lagged.reindex(full_daily_idx).ffill().fillna(False)
    return daily_signal.reindex(price_index, method="ffill").fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    lookback_weeks: int = 52,
    low_pct: float = 0.10,
    report_lag_days: int = 3,
) -> pd.Series:
    """Long only when E-mini S&P 500 leveraged-money net position is in the
    bottom `low_pct` percentile of its trailing `lookback_weeks` distribution
    (extreme bearish crowding -> contrarian long)."""
    df = _prep(price_df)
    signal = _extreme_short_fade_signal(df.index, lookback_weeks, low_pct, report_lag_days)
    return signal.astype(float)


def generate_returns(
    price_df: pd.DataFrame,
    lookback_weeks: int = 52,
    low_pct: float = 0.10,
    report_lag_days: int = 3,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df, lookback_weeks=lookback_weeks, low_pct=low_pct, report_lag_days=report_lag_days
    )
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
