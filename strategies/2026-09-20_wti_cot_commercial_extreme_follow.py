"""Strategy: CFTC COT WTI Crude Oil commercial-hedger ("smart money") extreme
net-position follow signal.

Hypothesis (see knowledge_base/strategies_log.jsonl id 2026-09-20-039):
Third COT-based strategy this cron trigger, third distinct market (Bitcoin
futures -037 rejected, Gold futures -038 accepted) and a THIRD distinct
COT category: commercial hedgers (not leveraged-money/non-commercial
speculators). Per TradeAlgo/cotinsight.com/TradingView COT-education pages
read via browser_exec this iteration: commercial hedgers are the
"smart money" side of the COT report (producers/consumers with genuine
physical-market information), and while retail COT lore usually treats
SPECULATOR extremes as a contrarian-fade signal, several of the same
sources note the alternate, equally-common framing that commercial
positioning EXTREMES (relative to the hedger's own multi-year net-position
history, since commercials are structurally net-short crude oil as
producers hedging output) can themselves be read as a bottom-calling
signal: when commercials reduce their usual net-short hedge book to an
unusually LOW net-short level (i.e. their own percentile rank is HIGH
relative to their trailing distribution), it means the "smart money"
sees less need to hedge against further downside, i.e. a bullish tell.
This strategy follows (not fades) that commercial-positioning extreme:
long WTI crude oil (proxied by USO) when the commercial net position
(comm_long - comm_short) percentile-ranks in the TOP `high_pct` of its own
trailing `lookback_weeks` distribution (commercials near-least-short they
have been), flat otherwise.

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
_WTI_MARKET = "WTI FINANCIAL CRUDE OIL - NEW YORK MERCANTILE EXCHANGE"


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return df


def _fetch_wti_comm_net() -> pd.Series:
    if _WTI_MARKET in _cot_cache:
        return _cot_cache[_WTI_MARKET]

    params = {
        "$where": f"market_and_exchange_names='{_WTI_MARKET}'",
        "$select": "report_date_as_yyyy_mm_dd,comm_positions_long_all,comm_positions_short_all",
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
        _cot_cache[_WTI_MARKET] = series
        return series

    idx = pd.to_datetime([r["report_date_as_yyyy_mm_dd"] for r in data], utc=True)
    net = pd.Series(
        [float(r["comm_positions_long_all"]) - float(r["comm_positions_short_all"]) for r in data],
        index=idx,
    ).sort_index()
    net = net[~net.index.duplicated(keep="last")]
    _cot_cache[_WTI_MARKET] = net
    return net


def _extreme_follow_signal(
    price_index: pd.DatetimeIndex,
    lookback_weeks: int,
    high_pct: float,
    report_lag_days: int,
) -> pd.Series:
    net = _fetch_wti_comm_net()
    if net.empty:
        return pd.Series(False, index=price_index)

    pct_rank = net.rolling(lookback_weeks, min_periods=max(8, lookback_weeks // 4)).apply(
        lambda w: (w.rank(pct=True).iloc[-1]), raw=False
    )
    follow_long = pct_rank >= high_pct

    lagged_index = follow_long.index + pd.Timedelta(days=report_lag_days)
    follow_long_lagged = pd.Series(follow_long.values, index=lagged_index)

    full_daily_idx = pd.date_range(
        min(price_index.min(), follow_long_lagged.index.min()),
        max(price_index.max(), follow_long_lagged.index.max()),
        freq="D",
        tz="UTC",
    )
    daily_signal = follow_long_lagged.reindex(full_daily_idx).ffill().fillna(False)
    return daily_signal.reindex(price_index, method="ffill").fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    lookback_weeks: int = 104,
    high_pct: float = 0.90,
    report_lag_days: int = 3,
) -> pd.Series:
    """Long only when WTI commercial hedger net position (comm_long -
    comm_short) percentile-ranks in the top `high_pct` of its trailing
    `lookback_weeks` distribution (commercials at their least-short --
    smart-money bullish tell)."""
    df = _prep(price_df)
    signal = _extreme_follow_signal(df.index, lookback_weeks, high_pct, report_lag_days)
    return signal.astype(float)


def generate_returns(
    price_df: pd.DataFrame,
    lookback_weeks: int = 104,
    high_pct: float = 0.90,
    report_lag_days: int = 3,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df, lookback_weeks=lookback_weeks, high_pct=high_pct, report_lag_days=report_lag_days
    )
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
