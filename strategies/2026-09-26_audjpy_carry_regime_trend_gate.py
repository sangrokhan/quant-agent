"""Strategy: Equity/Crypto Trend-Following Gated by AUDJPY Carry-Trade Regime.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from LITFX's "Carry Trade Strategy: Complete Practical Guide"
(https://litfx.app/learn/carry-trade-strategy, read via browser_exec after
web_search returned this URL; page rendered fine so no fallback needed for
extraction itself, only for the initial keyword search which DDGS
backend served without issue this iteration): the classic FX carry trade
(long a high-interest-rate currency funded in a low-interest-rate one,
e.g. long AUD/JPY) is a well-known "risk-on" barometer -- carry trades
"perform better in risk-on environments... when investors rush into
safe-haven currencies like JPY/CHF/USD" carry unwinds sharply, i.e.
AUD/JPY weakness/downtrend is itself a risk-off signal. Source's own
disclosed macro/regime filter: "Require that a risk-on proxy (e.g. S&P
500) is above its 100-day SMA... If [risk-on conditions] fail, you skip
new entries" -- i.e. the source explicitly uses trend status of a carry
pair as a risk-on/risk-off gate that should apply broadly to risk assets,
not just the FX pair itself. This strategy inverts the direction: uses
AUD/JPY's OWN trend status (source's own "Trend filter": price above its
200-day SMA with 50-day SMA above 200-day SMA = bullish carry regime) as
a risk-on gate on the PRIMARY asset's (QQQ/SPY/BTC/ETH) trend-following
signal, since the carry-unwind mechanic is a widely-cited leading/
coincident indicator of broader risk-asset stress (2008, 2015 CHF unpeg,
2024 August unwind all coincided with equity/crypto drawdowns).

Mechanic tested: primary asset long only when BOTH (a) primary asset's own
close > SMA(trend_window), AND (b) AUD/JPY's carry-regime is bullish (its
own close > SMA(carry_ma_window) AND carry_fast_ma > carry_slow_ma, per
source's exact "50-day SMA above 200-day SMA" bullish-alignment rule).
Flat otherwise.

First FX-carry-trade-regime (AUD/JPY) cross-asset gate in this repo --
distinct from all prior yield-curve/credit-spread/VIX-based risk-on-risk-off
gates (only 1 prior "carry trade" keyword hit in strategies_index.jsonl,
that one for a different mechanic) and from all prior currency-pair
strategies (this repo currently has none using yfinance's =X FX tickers
as a cross-asset regime input).

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)

NOTE: needs a SECOND price series (AUD/JPY). Since grid_test.py's harness
only passes a single price_df, AUD/JPY data is fetched internally via
data/loaders.py at import time (module-level cache) so the standard
single-price_df signature still works for the grid harness.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

_audjpy_cache: dict = {}


def _get_audjpy() -> pd.DataFrame:
    key = "AUDJPY=X"
    if key not in _audjpy_cache:
        import sys
        import os

        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
        from loaders import load_equity

        _audjpy_cache[key] = load_equity(key, datetime(2010, 1, 1), datetime(2026, 12, 31), interval="1d")
    return _audjpy_cache[key]


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 100,
    carry_ma_window: int = 200,
    carry_fast_window: int = 50,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long only while (a) primary asset close > SMA(trend_window) AND
    (b) AUD/JPY close > SMA(carry_ma_window) AND SMA(carry_fast_window) >
    SMA(carry_ma_window) (bullish carry-regime alignment, per source's own
    "50-day SMA above 200-day SMA" rule).
    """
    df = _prep(price_df)
    idx = df.index
    close = df["close"]

    trend_ok = close > close.rolling(trend_window).mean()

    audjpy_df = _prep(_get_audjpy())
    audjpy_close = audjpy_df["close"]
    audjpy_slow = audjpy_close.rolling(carry_ma_window).mean()
    audjpy_fast = audjpy_close.rolling(carry_fast_window).mean()
    carry_ok_raw = (audjpy_close > audjpy_slow) & (audjpy_fast > audjpy_slow)

    # Align AUD/JPY's (potentially different-timezone/tz-naive) daily index
    # onto the primary asset's index via forward-fill on the shared
    # calendar-date, taking the latest known AUD/JPY state as of each
    # primary-asset trading day.
    carry_ok_by_date = carry_ok_raw.copy()
    carry_ok_by_date.index = carry_ok_by_date.index.tz_localize(None) if carry_ok_by_date.index.tz is not None else carry_ok_by_date.index
    carry_ok_by_date = carry_ok_by_date[~carry_ok_by_date.index.duplicated(keep="last")]

    idx_naive = idx.tz_localize(None) if idx.tz is not None else idx
    carry_ok_reindexed = carry_ok_by_date.reindex(idx_naive, method="ffill").fillna(False)
    carry_ok_reindexed.index = idx

    position = (trend_ok & carry_ok_reindexed).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 100,
    carry_ma_window: int = 200,
    carry_fast_window: int = 50,
) -> pd.Series:
    """Daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        trend_window=trend_window,
        carry_ma_window=carry_ma_window,
        carry_fast_window=carry_fast_window,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_ret
