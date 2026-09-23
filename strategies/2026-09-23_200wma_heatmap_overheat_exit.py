"""Strategy: Bitcoin 200-Week Moving Average Heatmap Regime (Overheat Exit).

Hypothesis (2026-09-23, 8th iteration this cron trigger):
Per https://www.lookintobitcoin.com/charts/200-week-moving-average-heatmap/
(Plan B / @100trillionUSD, Jan 2019 concept, found via browser_exec after
web_search DDGS/Yahoo backend TLS-errored this iteration): "In each of its
major market cycles, Bitcoin's price historically bottoms out around the
200 week moving average... a colour heatmap [is assigned] based on the
% increases of that 200 week moving average [itself, month-over-month].
Historically, when we see... a good time to sell Bitcoin as the market
overheats [is when the 200WMA's own MoM growth rate is high]. Periods
where the price... [is] close to the 200 week MA have historically been
good times to buy."

The source's proprietary color-band thresholds are not publicly disclosed
(subscription-gated), so this operationalizes the DESCRIBED mechanism from
first principles using the source's own two stated conditions:

1. "Buy" condition: price is close to (within `near_band_pct` of) or below
   its own 200-week SMA -- the source's stated historical-bottom proxy.
2. "Overheat/sell" condition: the 200-week SMA's own trailing
   month-over-month (21-trading-day) percentage growth rate exceeds the
   `overheat_pctile`-th percentile of its own rolling history (a
   data-driven proxy for the source's "orange/red" overheating color
   bands, since the source doesn't publish its exact numeric cutoffs).

Long when NOT in overheat condition (i.e. below the overheat percentile
threshold); flat when the 200WMA's own MoM growth is in its own historical
overheated tail. This directly tests the source's own framing: it is a
SELL/reduce-exposure signal driven by the RATE OF CHANGE of the trend
line itself (not the price-vs-trend distance, which this repo's other BTC
strategies like Pi Cycle Top already test in different ways) -- first
strategy in this repo using the 200-week MA's own momentum as the primary
signal, rather than price crossing/distance from a moving average.

First 200-week-MA-based strategy in this repo (0 prior KB hits for "200
week"/"200WMA"). Equity (QQQ, SPY) tested as a falsification check since
the "market cycle overheating" framing is Bitcoin-specific halving-cycle
folklore with no obvious equity analog, though a 200-week (~4-year) MA
momentum signal is mechanically computable on any asset.
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
    wma_weeks: int = 200,
    mom_window_days: int = 21,
    overheat_pctile: float = 0.85,
    overheat_lookback_days: int = 756,
) -> pd.Series:
    """Return a {0,1} long/flat position series: long unless the 200-week
    SMA's own trailing MoM growth rate is in its own historical overheated
    tail (top `overheat_pctile` percentile over `overheat_lookback_days`)."""
    df = _prep(price_df)
    close = df["close"]

    wma_days = wma_weeks * 7
    sma200w = close.rolling(wma_days, min_periods=max(30, wma_days // 4)).mean()

    # Month-over-month (mom_window_days) growth rate of the 200-week SMA itself.
    wma_mom_growth = sma200w.pct_change(mom_window_days)

    # Rolling percentile threshold of the WMA's own MoM growth history
    # (data-driven proxy for the source's proprietary color-band cutoffs).
    rolling_threshold = wma_mom_growth.rolling(
        overheat_lookback_days, min_periods=max(60, overheat_lookback_days // 4)
    ).quantile(overheat_pctile)

    overheated = wma_mom_growth > rolling_threshold
    position = (~overheated.fillna(False)).astype(int)

    # No signal possible before the 200-week SMA itself has enough data.
    position[sma200w.isna()] = 0
    position.index = close.index
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs). Position lagged by 1 day."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
