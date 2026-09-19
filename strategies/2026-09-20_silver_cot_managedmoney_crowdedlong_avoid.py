"""Strategy: CFTC COT Silver Managed-Money extreme net-long contrarian fade.

Hypothesis (see knowledge_base/strategies_log.jsonl id 2026-09-20-042):
Sixth COT-based strategy this cron trigger, sixth distinct market/report
type (Silver futures via the CFTC's "Disaggregated" report format, which
splits speculators into "Managed Money" -- CTAs/hedge funds/commodity
pool operators -- rather than the "Legacy" report's undifferentiated
non-commercial category used for Gold/WTI/E-mini-S&P earlier this cron
trigger). Per MetalCharts.org's own Silver COT education page ("What are
extreme levels for silver Managed Money positioning? Silver Managed Money
net positioning extremes vary over time, but readings above 60,000 to
70,000 [contracts]...") and markettriage.com/TradingView COT-education
pages read via browser_exec this iteration: Managed Money speculators in
Silver futures are prone to herding into extreme net-long positions near
local price tops (they chase momentum on the way up, then have nowhere
left to add), making an extreme-net-long percentile a contrarian SHORT-
avoidance signal on the long-only backtest convention used throughout
this repo -- i.e. go FLAT (not short) when Managed Money net position is
in the top `high_pct` percentile of its own trailing `lookback_weeks`
distribution (crowded-long, elevated pullback risk), long otherwise
(default-long framing, the opposite polarity from the extreme-fade
strategies applied to Bitcoin/E-mini-S&P earlier this trigger, which
faded extreme SHORTS into longs -- this one fades extreme LONGS into
flat).

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
_SILVER_MARKET = "SILVER - COMMODITY EXCHANGE INC."


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return df


def _fetch_silver_mm_net() -> pd.Series:
    if _SILVER_MARKET in _cot_cache:
        return _cot_cache[_SILVER_MARKET]

    params = {
        "$where": f"market_and_exchange_names='{_SILVER_MARKET}'",
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
        _cot_cache[_SILVER_MARKET] = series
        return series

    idx = pd.to_datetime([r["report_date_as_yyyy_mm_dd"] for r in data], utc=True)
    net = pd.Series(
        [float(r["m_money_positions_long_all"]) - float(r["m_money_positions_short_all"]) for r in data],
        index=idx,
    ).sort_index()
    net = net[~net.index.duplicated(keep="last")]
    _cot_cache[_SILVER_MARKET] = net
    return net


def _crowded_long_flag(
    price_index: pd.DatetimeIndex,
    lookback_weeks: int,
    high_pct: float,
    report_lag_days: int,
) -> pd.Series:
    net = _fetch_silver_mm_net()
    if net.empty:
        return pd.Series(False, index=price_index)

    pct_rank = net.rolling(lookback_weeks, min_periods=max(8, lookback_weeks // 4)).apply(
        lambda w: (w.rank(pct=True).iloc[-1]), raw=False
    )
    crowded = pct_rank >= high_pct

    lagged_index = crowded.index + pd.Timedelta(days=report_lag_days)
    crowded_lagged = pd.Series(crowded.values, index=lagged_index)

    full_daily_idx = pd.date_range(
        min(price_index.min(), crowded_lagged.index.min()),
        max(price_index.max(), crowded_lagged.index.max()),
        freq="D",
        tz="UTC",
    )
    daily_signal = crowded_lagged.reindex(full_daily_idx).ffill().fillna(False)
    return daily_signal.reindex(price_index, method="ffill").fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    lookback_weeks: int = 156,
    high_pct: float = 0.90,
    report_lag_days: int = 3,
) -> pd.Series:
    """Default-long; go flat when Silver Managed Money net position is in
    the top `high_pct` percentile of its trailing `lookback_weeks`
    distribution (crowded-long speculators, elevated pullback risk)."""
    df = _prep(price_df)
    crowded = _crowded_long_flag(df.index, lookback_weeks, high_pct, report_lag_days).astype(bool)
    position = (~crowded).astype(float)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    lookback_weeks: int = 156,
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
