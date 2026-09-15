"""Strategy: Halloween Effect / "Sell in May and Go Away" seasonal calendar
strategy (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's
id): per the well-documented "Halloween Effect" seasonal anomaly (Google
search synthesis of Quantified Strategies, Emerald/academic literature,
Seasonality360, Investopedia), equity market returns from November 1
through April 30 (the "winter" half) are historically stronger than
returns from May 1 through October 31 (the "summer" half) -- "sell in May
and go away, come back on St. Leger's Day [~mid-Sept, simplified here to
Nov 1]". Distinct from this repo's existing "Turn-of-Month" (2026-09-11-124,
day-of-month) and "day-of-week" seasonality entries -- this is a
half-year calendar-window rule, not tested in this repo under this
specific 6-month framing.

Sources read this iteration:
- Google search results synthesis of Halloween Effect / Sell in May
  numeric calendar rules (Quantified Strategies, Emerald academic journal,
  Seasonality360, Investopedia, IG.com).

Signal logic
------------
- Long (fully invested) from Nov 1 through Apr 30 (inclusive) of each
  year -- the "winter"/favorable half.
- Flat from May 1 through Oct 31 -- the "summer"/unfavorable half.
- No stop-loss/take-profit (pure calendar rule per source's own framing);
  exposed to full market drawdowns during the winter half by design.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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
    favorable_start_month: int = 11,
    favorable_end_month: int = 4,
) -> pd.Series:
    df = _prep(price_df)
    idx = df.index
    months = idx.month

    if favorable_start_month > favorable_end_month:
        # wraps around year-end, e.g. Nov(11) -> Apr(4)
        in_favorable = (months >= favorable_start_month) | (months <= favorable_end_month)
    else:
        in_favorable = (months >= favorable_start_month) & (months <= favorable_end_month)

    position = pd.Series(in_favorable.astype(int), index=idx)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    favorable_start_month: int = 11,
    favorable_end_month: int = 4,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_returns = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        favorable_start_month=favorable_start_month,
        favorable_end_month=favorable_end_month,
    )
    strat_returns = daily_returns * position.shift(1).fillna(0)
    return strat_returns
