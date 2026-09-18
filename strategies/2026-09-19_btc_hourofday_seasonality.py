"""Strategy: Bitcoin/crypto hour-of-day intraday seasonality window hold.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-19-002):
Per Quantpedia's "The Seasonality of Bitcoin" research (summarized in
https://www.quantifiedstrategies.com/bitcoin-intraday-seasonality-trading-strategy/,
read via browser_exec after web_search DDGS backend returned no usable
results): Bitcoin's 24/7 market shows a robust intraday-hour seasonal
pattern -- average hourly returns peak around 21:00-23:00 UTC (coinciding
with the US trading-day close / evening liquidity window), driven by
recurring liquidity/flow timing rather than randomness. The source's own
simple strategy: hold BTC ONLY during a narrow window of peak hours each
day, flat otherwise, which the source claims outperforms buy-and-hold on a
risk-adjusted basis with far less market exposure. This strategy holds a
long position only during an entry_hour..exit_hour UTC window each day
(both hourly-bar boundaries, e.g. 21:00 through 23:00 UTC), flat all other
hours, optionally gated by a long-term SMA trend filter (source notes "a
200-day SMA filter improves returns slightly").

Signal logic (crypto, 1h bars only -- equity loader here is daily-only so
this genuinely intraday-seasonality idea cannot be tested on equities with
available data; scope is honestly crypto-only)
-----------------------------------------------------------------------
- Long only when the bar's UTC hour is within [entry_hour, exit_hour)
  (wraps past midnight if exit_hour <= entry_hour).
- Optional trend filter: additionally require close > SMA(trend_window)
  (daily-equivalent trend proxy on hourly bars, trend_window in hours).
- Flat all other hours.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    entry_hour: int = 21,
    exit_hour: int = 23,
    trend_window: int = 0,  # 0 = no trend filter, else SMA window in bars (hours)
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    hours = df.index.hour
    if entry_hour < exit_hour:
        in_window = (hours >= entry_hour) & (hours < exit_hour)
    else:
        # wraps past midnight UTC
        in_window = (hours >= entry_hour) | (hours < exit_hour)

    in_window = pd.Series(in_window, index=df.index)

    if trend_window and trend_window > 0:
        sma = close.rolling(trend_window).mean()
        trend_ok = close > sma
    else:
        trend_ok = pd.Series(True, index=df.index)

    position = (in_window & trend_ok).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    entry_hour: int = 21,
    exit_hour: int = 23,
    trend_window: int = 0,
) -> pd.Series:
    """Return the strategy's per-bar returns (no transaction costs applied)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df, entry_hour=entry_hour, exit_hour=exit_hour, trend_window=trend_window
    )
    # Signal known at bar close -> position held for the NEXT bar's return
    bar_return = close.pct_change().fillna(0.0)
    strat_return = position.shift(1).fillna(0) * bar_return
    return strat_return
