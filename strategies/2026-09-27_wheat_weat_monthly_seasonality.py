"""Strategy: Wheat (WEAT ETF proxy) monthly seasonality calendar (long-only
adaptation of the source's own disclosed month-by-month bull/bear windows).

Hypothesis (2026-09-27 KB entry, this iteration): per
https://forecaster.biz/seasonality/commodities/wheat/ (Wheat/KE monthly
seasonality study, 5/7/10-year historical win-rate backtest disclosed per
calendar month), wheat futures exhibit a repeating annual pattern: bullish
(long-favored) in Feb-May and Aug-Sept-Nov, bearish (short-favored) in
Dec-Jan and June-July and October. Per SAFETY.md (long-only, no
short-selling execution code), this strategy holds WEAT only during the
source's own disclosed LONG-favored months (Feb, Mar, Apr, May, Aug, Sep,
Nov) and stays flat during the source's SHORT-favored months (Dec, Jan,
Jun, Jul, Oct) -- i.e. going flat rather than short during unfavorable
months, a standard long-only adaptation already used elsewhere in this repo
for seasonality strategies with disclosed short legs (e.g. Sell-in-May,
Turn-of-Month). First Wheat/WEAT and first grain-commodity seasonality
strategy in this repo (0 prior KB hits for wheat/WEAT/corn/CORN/soybean
seasonality) -- distinct from all other calendar-anomaly strategies already
tested (turn-of-month, pre-holiday, day-of-week, Halloween indicator) since
none of those are commodity-specific agricultural-cycle (planting/growing/
harvest) seasonality.

Signal logic:
    long_months = {feb, mar, apr, may, aug, sep, nov} (source's disclosed
                   long-favored months, param-configurable)
    position[t] = 1 if month(t) in long_months else 0

Interface contract for validators/grid_test (see RESEARCH_LOOP.md Step 5):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd

_DEFAULT_LONG_MONTHS = (2, 3, 4, 5, 8, 9, 11)


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    long_months: tuple = _DEFAULT_LONG_MONTHS,
) -> pd.Series:
    """Return a {0,1} long/flat position series, long only during the
    source's disclosed bullish-seasonality calendar months."""
    df = _prep(price_df)
    close = df["close"]
    months = close.index.month
    position = pd.Series(
        [1 if m in long_months else 0 for m in months],
        index=close.index,
        dtype=int,
    )
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
