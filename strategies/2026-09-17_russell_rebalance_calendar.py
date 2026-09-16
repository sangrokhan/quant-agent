"""Strategy: Russell 2000 (IWM) annual index-rebalancing seasonal effect.

Hypothesis (this iteration's research; web_search DDGS backend errored
with TLS RequestError -> browser_exec Google SERP fallback used
throughout): per QuantifiedStrategies.com's "The Small-Cap Rally That
Happens Once a Year" article (confirmed via Google search snippet this
iteration -- full article behind a paywall beyond the summary, but the
exact numeric rule surfaced verbatim in the search snippet): "The strategy
uses two simple rules: Buy on the close of the first trading day after
June 23rd. Sell on the close of the first trading day of July." This
exploits the well-documented Russell index annual reconstitution (all
Russell indexes reconstitute after the close on the fourth Friday of
June), which creates predictable buy-side imbalances in small-cap stocks
as index funds rebalance -- a mechanism-grounded calendar anomaly
distinct from every prior calendar-effect strategy tested in this repo
(turn-of-month, day-of-week, pre-holiday, Halloween indicator, etc. --
none of which are keyed to a specific annual corporate-action-style event
date). Source's own reported backtest (cash index, since 2000): 38 trades,
avg gain 1.2%/trade, win ratio 73%, profit factor 3, MDD 6%, ~2%
time-in-market.

Tested here on IWM (the ETF ticker the source itself uses) as the primary
symbol, plus QQQ/SPY/crypto as falsification checks (this repo's standard
practice) since the Russell-specific rebalancing mechanism should NOT
apply to non-Russell-tracking assets.

Interface contract: both generate_signals and generate_returns accept all
tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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
    entry_after_day: int = 23,
    entry_month: int = 6,
) -> pd.Series:
    """Return a 0/1 position series.

    Long from the close of the first trading day after ``entry_after_day``
    of ``entry_month`` (default June 23) through the close of the first
    trading day of the following month (July), per the source's exact
    two-rule specification. Flat otherwise.
    """
    df = _prep(price_df)
    close = df["close"]
    idx = close.index

    position = pd.Series(0, index=idx, dtype=int)

    years = sorted(set(idx.year))
    for year in years:
        # Entry: first trading day strictly after entry_month/entry_after_day.
        entry_candidates = idx[(idx.year == year) & (idx.month == entry_month) & (idx.day > entry_after_day)]
        if len(entry_candidates) == 0:
            continue
        entry_date = entry_candidates[0]

        # Exit: first trading day of the following month (July).
        next_month = entry_month + 1
        next_month_year = year
        if next_month > 12:
            next_month = 1
            next_month_year = year + 1
        exit_candidates = idx[(idx.year == next_month_year) & (idx.month == next_month)]
        if len(exit_candidates) == 0:
            continue
        exit_date = exit_candidates[0]

        # Long from entry_date's close through exit_date's close: position
        # is 1 on every bar strictly after entry_date up to and including
        # exit_date (captures entry_date->exit_date's close-to-close return
        # via the shift(1) in generate_returns).
        mask = (idx > entry_date) & (idx <= exit_date)
        position.loc[mask] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
