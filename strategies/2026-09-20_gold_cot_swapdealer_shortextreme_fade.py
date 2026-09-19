"""Strategy: CFTC COT Gold Swap-Dealer extreme-net-short contrarian fade.

Hypothesis (see knowledge_base/strategies_log.jsonl id 2026-09-20-045):
Ninth COT-based strategy this cron trigger, but a NEW COT CATEGORY on an
already-used market: Gold's "Swap Dealer" positioning (CFTC Disaggregated
report -- bullion banks/OTC-market-makers hedging their client books,
distinct from the "non-commercial"/speculator category already tested
for Gold in this trigger's accepted strategy -038). Per
silverdominion.com's live commentary ("Swap dealers are currently net
short gold by an amount equal to 58.2% of total open interest") and
cotinsight.com's "Gold has an unusually important swap-dealer layer...
intermediate between the OTC market and futures market" (both read via
browser_exec this iteration): swap dealers in gold run a structurally
massive net-short book (hedging client long exposure written OTC), and
when that net-short position becomes even MORE extreme than usual
(bottom `low_pct` percentile of its own trailing `lookback_weeks`
distribution), it implies dealers have absorbed an unusually large amount
of client buying pressure -- a contrarian bullish tell (dealers are
"tapped out" on their hedge book, mirroring the same percentile-extreme-
fade logic already applied to Bitcoin leveraged-money -037 and E-mini S&P
-041, but on a THIRD distinct category (swap dealer vs leveraged-money)
and REUSING gold's existing dataset with a different field).

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
_GOLD_MARKET = "GOLD - COMMODITY EXCHANGE INC."


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return df


def _fetch_gold_swap_net() -> pd.Series:
    if _GOLD_MARKET in _cot_cache:
        return _cot_cache[_GOLD_MARKET]

    params = {
        "$where": f"market_and_exchange_names='{_GOLD_MARKET}'",
        "$select": "report_date_as_yyyy_mm_dd,swap_positions_long_all,swap__positions_short_all",
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
        [float(r["swap_positions_long_all"]) - float(r["swap__positions_short_all"]) for r in data],
        index=idx,
    ).sort_index()
    net = net[~net.index.duplicated(keep="last")]
    _cot_cache[_GOLD_MARKET] = net
    return net


def _extreme_short_fade_signal(
    price_index: pd.DatetimeIndex,
    lookback_weeks: int,
    low_pct: float,
    report_lag_days: int,
) -> pd.Series:
    net = _fetch_gold_swap_net()
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
    return daily_signal.reindex(price_index, method="ffill").fillna(False).astype(bool)


def generate_signals(
    price_df: pd.DataFrame,
    lookback_weeks: int = 156,
    low_pct: float = 0.10,
    report_lag_days: int = 3,
) -> pd.Series:
    """Long only when Gold swap-dealer net position is in the bottom
    `low_pct` percentile of its trailing `lookback_weeks` distribution
    (dealers unusually more net-short than normal -> contrarian long)."""
    df = _prep(price_df)
    signal = _extreme_short_fade_signal(df.index, lookback_weeks, low_pct, report_lag_days)
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
