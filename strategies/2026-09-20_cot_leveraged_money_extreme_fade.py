"""Strategy: CFTC COT "Leveraged Money" net-positioning extreme contrarian fade.

Hypothesis (see knowledge_base/strategies_log.jsonl id 2026-09-20-037):
Per CFTC.gov's own Commitments of Traders (COT) report documentation and
multiple trading-education sources (TradeAlgo AI summary, FP Markets,
Oanda education pages) read via browser_exec this iteration: the weekly
COT report's "Leveraged Money" category (CME's non-commercial /
speculator-equivalent classification introduced for financial futures)
reaches statistical extremes -- its net position (long - short) sitting in
the top or bottom decile of its own trailing 3-year (156-week) rolling
distribution -- that historically precede mean-reverting price moves, the
classic "everyone already long/short, no one left to push it further"
crowding signal. This is the FIRST strategy in this repo to use CFTC COT
data (a brand-new, previously-untapped weekly-cadence dataset, fetched
live from the CFTC Socrata public API at publicreporting.cftc.gov,
confirmed feasible this iteration: BITCOIN futures COT history is
available weekly back to 2017-12-19, ~875 rows). Applied here to CME
Bitcoin futures (proxying BTC/USDT price via this repo's existing crypto
loader) since it is the one COT-covered market plausibly correlated with
an asset class already in this repo's grid-test universe; equity legs of
the grid use SPY/QQQ price data driven by the SAME BTC-COT-derived signal
purely as an out-of-sample cross-asset-class robustness check (no
COT-native equity-index-futures signal is used here -- if the BTC-COT
signal, applied blind, "worked" on SPY/QQQ that would itself be
suspicious/overfit, so seeing it NOT transfer to equities is the expected,
honest outcome and does not invalidate the crypto-only reading).

Signal logic
------------
- net_lev_money[t] = lev_money_positions_long[t] - lev_money_positions_short[t]
  (percentile-ranked over its own trailing `lookback_weeks` window, e.g. 156
  weeks = 3 years, per the source's own convention).
- percentile[t] = rolling percentile rank of net_lev_money[t] within the
  trailing `lookback_weeks` window.
- Long (fade extreme-short crowding) when percentile[t] <= low_pct (e.g.
  0.10): leveraged-money speculators are historically as net-short as
  they've been in `lookback_weeks` weeks -> contrarian long.
- Flat/short-avoidance otherwise for this long-only backtest convention
  (repo standard: long-only, {0,1} positions) -- percentile[t] >= high_pct
  (e.g. 0.90) is treated as flat (avoid, don't go short) rather than an
  explicit short leg, consistent with this repo's other contrarian
  strategies' long-only convention.
- The weekly COT print is forward-filled onto the daily price index with a
  `report_lag_days` (default 3, matching the report's own Tuesday-data/
  Friday-3:30pm-ET-release convention cited by the source) delay to avoid
  look-ahead bias.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import pandas as pd

_cot_cache: dict = {}

_COT_ENDPOINT = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return df


def _fetch_cot_net_lev_money(market_like: str = "BITCOIN") -> pd.Series:
    """Fetch weekly net leveraged-money position for a COT market, cached."""
    if market_like in _cot_cache:
        return _cot_cache[market_like]

    where = f"market_and_exchange_names like '%{market_like}%'"
    params = {
        "$where": where,
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
        _cot_cache[market_like] = series
        return series

    idx = pd.to_datetime([r["report_date_as_yyyy_mm_dd"] for r in data], utc=True)
    net = pd.Series(
        [float(r["lev_money_positions_long"]) - float(r["lev_money_positions_short"]) for r in data],
        index=idx,
    ).sort_index()
    net = net[~net.index.duplicated(keep="last")]
    _cot_cache[market_like] = net
    return net


def _extreme_long_signal(
    price_index: pd.DatetimeIndex,
    lookback_weeks: int,
    low_pct: float,
    report_lag_days: int,
) -> pd.Series:
    net = _fetch_cot_net_lev_money("BITCOIN")
    if net.empty:
        return pd.Series(False, index=price_index)

    pct_rank = net.rolling(lookback_weeks, min_periods=max(8, lookback_weeks // 4)).apply(
        lambda w: (w.rank(pct=True).iloc[-1]), raw=False
    )
    fade_long = pct_rank <= low_pct

    # Apply report lag: signal known `report_lag_days` after the report_date.
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
    lookback_weeks: int = 156,
    low_pct: float = 0.10,
    report_lag_days: int = 3,
) -> pd.Series:
    """Long only when BTC futures leveraged-money net position is in the
    bottom `low_pct` percentile of its trailing `lookback_weeks` distribution
    (extreme-short crowding -> contrarian long)."""
    df = _prep(price_df)
    signal = _extreme_long_signal(df.index, lookback_weeks, low_pct, report_lag_days)
    return signal.astype(float)


def generate_returns(
    price_df: pd.DataFrame,
    lookback_weeks: int = 156,
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
