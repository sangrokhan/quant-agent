"""Strategy: Turn-of-the-Month (TOM) seasonality, trend-filtered follow-up.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-125):
Direct fix attempt for rejected 2026-09-11-124 (plain TOM seasonality,
Sharpe 0.73/0.78 on QQQ/SPY, near-miss vs 1.0 threshold, QQQ also
marginally exceeded MDD). That entry's own notes flagged: "edge
concentrates in low-vol regimes (17/36 low vs 4/36 mid, 5/36 high) --
adding [a trend/vol] gate explicitly ... could push full-sample Sharpe
above 1.0." This iteration adds exactly that: an explicit close >
SMA(trend_window) trend filter on top of the same calendar-window logic,
so TOM entries only fire when the broader market is already in an uptrend
(avoiding the mid/high-vol-regime TOM entries that dragged down the
un-gated version's full-sample Sharpe).

Same underlying calendar mechanism and source as 2026-09-11-124 (Google
AI-overview synthesis of ScienceDirect/QuantPedia/Forbes Turn-of-the-Month
literature): long from entry_days_before_month_end-th-to-last trading day
of the month through exit_days_into_month-th trading day of the next
month, but ONLY if close > SMA(trend_window) on the day the entry window
opens.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (position: {0,1})
    generate_returns(price_df, **params) -> pd.Series
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
    entry_days_before_month_end: int = 6,
    exit_days_into_month: int = 2,
    trend_window: int = 100,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    idx = df.index

    ym = pd.Series(idx.year * 100 + idx.month, index=idx)
    rank_from_start = ym.groupby(ym).cumcount()
    rank_from_end = ym.groupby(ym).cumcount(ascending=False)

    in_calendar_window = (rank_from_end <= entry_days_before_month_end) | (rank_from_start <= exit_days_into_month)

    sma_trend = close.rolling(trend_window).mean()
    trend_ok = close > sma_trend

    position = (in_calendar_window & trend_ok.fillna(False)).astype(int)
    position.index = idx
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
