"""Strategy: Monthly Options Expiration Day Short (opex intraday short).

Hypothesis (see knowledge_base/strategies_log.jsonl):
Per QuantifiedStrategies.com's "A Rare Day Trading Strategy for the Short
Side" (https://www.quantifiedstrategies.com/a-rare-day-trading-strategy-for-
the-short-side/, disclosed rule per the article's own Google AI-overview
summary and its stated performance table): order imbalances on monthly
options expiration days (the third Friday of each month) tend to produce
weak price action after the opening auction. The disclosed rule: identify
the third Friday of the month, short the market at the open, cover at the
close (source's own QQQ backtest: 322 trades, 58% win rate, profit factor
1.7, average gain 0.23%/trade, only 4% total market exposure). This is
distinct from the already-rejected Quad Witching pre/post multi-day WINDOW
strategy (2026-09-19-053, which trades the days AROUND a quarterly-only
witching Friday) -- this strategy trades every MONTHLY third-Friday
directly, intraday (open-to-close), short side, using this repo's daily
OHLC bars to approximate the source's exact open-to-close mechanic (return
= -(close-open)/open on the trigger day, flat otherwise).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series

Note: generate_signals returns a {0,-1} series (short = -1), since this is
inherently a short-only day-trade strategy per the source's own disclosed
rule -- generate_returns computes the return directly from open-to-close
rather than close-to-close*position, to correctly capture the intraday
short mechanic on the trigger day itself.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _third_friday_mask(index: pd.DatetimeIndex, day_min: int = 15, day_max: int = 21) -> pd.Series:
    """True on trading days that are the third Friday of their month (or,
    if the exact third Friday isn't a trading day due to a holiday, the
    nearest preceding trading day within the same week -- approximated
    here simply by matching Friday weekday + a day-of-month window)."""
    is_friday = index.weekday == 4
    is_third_week = (index.day >= day_min) & (index.day <= day_max)
    return pd.Series(is_friday & is_third_week, index=index)


def generate_signals(
    price_df: pd.DataFrame,
    day_min: int = 15,
    day_max: int = 21,
    quarterly_only: bool = False,
) -> pd.Series:
    df = _prep(price_df)
    trigger = _third_friday_mask(df.index, day_min, day_max)
    if quarterly_only:
        trigger = trigger & df.index.month.isin([3, 6, 9, 12])
    position = pd.Series(0, index=df.index, dtype=int)
    position[trigger] = -1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    day_min: int = 15,
    day_max: int = 21,
    quarterly_only: bool = False,
) -> pd.Series:
    df = _prep(price_df)
    trigger = _third_friday_mask(df.index, day_min, day_max)
    if quarterly_only:
        trigger = trigger & df.index.month.isin([3, 6, 9, 12])
    intraday_return = (df["close"] - df["open"]) / df["open"]
    strat_returns = pd.Series(0.0, index=df.index)
    strat_returns[trigger] = -intraday_return[trigger]
    return strat_returns
