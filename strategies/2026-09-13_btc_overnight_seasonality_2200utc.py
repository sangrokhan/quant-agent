"""Strategy: Overnight Seasonality in Bitcoin (hourly seasonality effect).

Source: Quantpedia "Overnight Seasonality in Bitcoin"
(https://quantpedia.com/strategies/intraday-seasonality-in-bitcoin), citing
Padysak & Vojtko "Seasonality, Trend-following, and Mean reversion in
Bitcoin" (SSRN 4081000). Fully disclosed mechanical rule from the source's
own "Simple trading strategy" section:

    "open a long position in the BTC at 22:00 (UTC+0) and hold it for two
    hours. The position is closed after the two hour holding period."

Source's own stated rationale: BTC trades 24/7 but 22:00-23:00 UTC is the
one window when every major traditional exchange (NYSE, Tokyo, Hong Kong,
India, Australia, London) is simultaneously closed, so it captures a
distinct pocket of crypto-specific demand/liquidity untouched by
traditional-market arbitrage flows. Source reports 33% annualized return,
20.93% vol, Sharpe 1.58, MDD -34.04% over its own 2015-2021 Gemini-exchange
sample (pre-transaction-cost, single-instrument).

This repo generalizes the entry hour (`entry_hour`, default 22 per source)
and hold length (`hold_hours`, default 2 per source) as tunable params for
the grid test, since the exact best hour/window could differ on this repo's
Binance-hourly-bar sample vs. the source's own 2015-2021 Gemini sample.

Genuinely novel construction in this repo: first HOURLY-bar, hour-of-day
seasonality strategy tested here (all prior seasonality entries in this
repo -- day-of-week, turn-of-month, weekend-effect -- operate on daily
bars). Not applicable to this repo's equity loader (daily bars only, no
NYSE hourly seasonality data source), so equity cells in the grid test
will be a null/feasibility-check control confirming this is a crypto-only,
intraday-only effect (source itself frames it as such).

Interface contract (see validation/grid_test.py, validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (per-bar strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    return df


def generate_signals(
    price_df: pd.DataFrame,
    entry_hour: int = 22,
    hold_hours: int = 2,
) -> pd.Series:
    """Return a {0,1} position series on HOURLY bars (1 = held during the
    entry_hour..entry_hour+hold_hours-1 UTC window each day; 0 otherwise).

    If price_df is not hourly (e.g. this repo's daily equity loader), this
    degrades to always-0 (feasibility-blocked / not applicable), which is
    the correct behavior for the grid's equity control cells.
    """
    df = _prep(price_df)
    idx = df.index
    if idx.tz is None:
        idx_utc_hour = idx.hour
    else:
        idx_utc_hour = idx.tz_convert("UTC").hour

    # Detect bar frequency: if median spacing isn't ~1 hour, this loader
    # gave us daily bars -- hour-of-day seasonality isn't testable, so
    # return an all-flat series (feasibility control, not an error).
    if len(idx) > 2:
        deltas = (idx[1:] - idx[:-1]).to_series().dt.total_seconds()
        median_delta_hours = deltas.median() / 3600.0
    else:
        median_delta_hours = 24.0

    if median_delta_hours >= 6.0:  # daily (or coarser) bars -- not applicable
        return pd.Series(0, index=df.index, dtype=int)

    entry_hours_set = {(entry_hour + h) % 24 for h in range(hold_hours)}
    position = pd.Series(
        [1 if h in entry_hours_set else 0 for h in idx_utc_hour],
        index=df.index, dtype=int,
    )
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Per-bar strategy returns: close-to-close return on bars where the
    position is active (1), 0 elsewhere. Since this is an hourly-bar
    strategy, the caller's Sharpe/MDD annualization elsewhere in this repo
    assumes periods_per_year=252 (daily) by default -- the grid/validator
    calls in this repo pass hourly bars through the same close-to-close
    daily-return-style pipeline, consistent with how this repo's other
    crypto strategies already treat 1h bars (see e.g.
    2026-09-09-040 Three White Soldiers hourly-bar entry).
    """
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)

    ret = close.pct_change().fillna(0.0)
    strat_ret = ret * position
    return strat_ret
