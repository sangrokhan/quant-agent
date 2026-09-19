"""Strategy: CFTC COT VIX-futures leveraged-money extreme-net-short
("complacency") SPY defensive gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id 2026-09-20-040):
Fourth COT-based strategy this cron trigger, fourth distinct market (VIX
futures, CBOE Futures Exchange -- first use of VIX-futures COT data in
this repo, confirmed feasible via direct Socrata API call: 1017 weekly
rows back to 2006). Per StockCircle/TradingView COT-education pages and
general "short-vol crowding precedes vol spikes" market lore (Feb 2018
"Volmageddon" being the canonical historical example, referenced by
Loomis Sayles' "How the Spike in Volatility Punctured the Short Vol
Trade" surfaced this iteration) read via browser_exec: leveraged-money
speculators in VIX futures are structurally net-SHORT (the "short vol"
carry trade, harvesting VIX futures' contango roll-down). When that
net-short position becomes EXTREME relative to its own trailing
`lookback_weeks` history (bottom `low_pct` percentile of net position,
i.e. more short than usual = complacency/crowded short-vol trade), the
market lacks marginal short-vol sellers left to keep suppressing
volatility, raising the risk of a sharp vol-spike/equity-drawdown event.
This strategy applies that as a DEFENSIVE GATE on SPY: hold SPY (trend
gate: close > SMA(trend_window)) UNLESS VIX-futures leveraged-money net
position is in its bottom `low_pct` trailing percentile (extreme
short-vol complacency), in which case go flat regardless of the equity
trend (crash-risk avoidance), similar in spirit to this repo's other
VIX-gated equity defensive strategies but using COT positioning instead
of the VIX level/term-structure itself.

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
_VIX_MARKET = "VIX FUTURES - CBOE FUTURES EXCHANGE"


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return df


def _fetch_vix_lev_money_net() -> pd.Series:
    if _VIX_MARKET in _cot_cache:
        return _cot_cache[_VIX_MARKET]

    params = {
        "$where": f"market_and_exchange_names='{_VIX_MARKET}'",
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
        _cot_cache[_VIX_MARKET] = series
        return series

    idx = pd.to_datetime([r["report_date_as_yyyy_mm_dd"] for r in data], utc=True)
    net = pd.Series(
        [float(r["lev_money_positions_long"]) - float(r["lev_money_positions_short"]) for r in data],
        index=idx,
    ).sort_index()
    net = net[~net.index.duplicated(keep="last")]
    _cot_cache[_VIX_MARKET] = net
    return net


def _complacency_flag(
    price_index: pd.DatetimeIndex,
    lookback_weeks: int,
    low_pct: float,
    report_lag_days: int,
) -> pd.Series:
    net = _fetch_vix_lev_money_net()
    if net.empty:
        return pd.Series(False, index=price_index)

    pct_rank = net.rolling(lookback_weeks, min_periods=max(8, lookback_weeks // 4)).apply(
        lambda w: (w.rank(pct=True).iloc[-1]), raw=False
    )
    complacent = pct_rank <= low_pct  # extreme net-short (most negative)

    lagged_index = complacent.index + pd.Timedelta(days=report_lag_days)
    complacent_lagged = pd.Series(complacent.values, index=lagged_index)

    full_daily_idx = pd.date_range(
        min(price_index.min(), complacent_lagged.index.min()),
        max(price_index.max(), complacent_lagged.index.max()),
        freq="D",
        tz="UTC",
    )
    daily_signal = complacent_lagged.reindex(full_daily_idx).ffill().fillna(False)
    return daily_signal.reindex(price_index, method="ffill").fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 100,
    lookback_weeks: int = 156,
    low_pct: float = 0.10,
    report_lag_days: int = 3,
) -> pd.Series:
    """Long SPY when close > SMA(trend_window) UNLESS VIX-futures
    leveraged-money net position is in the bottom `low_pct` percentile of
    its trailing `lookback_weeks` distribution (extreme short-vol
    complacency -> defensive flat)."""
    df = _prep(price_df)
    close = df["close"]
    trend_long = close > close.rolling(trend_window).mean()
    complacent = _complacency_flag(df.index, lookback_weeks, low_pct, report_lag_days)
    position = (trend_long.fillna(False) & ~complacent).astype(float)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 100,
    lookback_weeks: int = 156,
    low_pct: float = 0.10,
    report_lag_days: int = 3,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df, trend_window=trend_window, lookback_weeks=lookback_weeks,
        low_pct=low_pct, report_lag_days=report_lag_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
