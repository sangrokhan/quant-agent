"""Strategy: Natural gas storage-cycle seasonality -- long during the EIA
withdrawal season (heating-demand storage drawdown), flat during the
injection season.

Hypothesis (2026-09-27 KB entry, this iteration): per
https://tradefundrr.com/blog/natural-gas-seasonality-for-futures-traders
(citing the U.S. Energy Information Administration), the natural gas
storage year splits into an injection season (April 1 - October 31, supply
builds storage ahead of winter) and a withdrawal season (November 1 -
March 31, heating demand draws storage down). The source frames this as a
risk/volatility-sizing context rather than a disclosed directional trading
rule, so this iteration encodes the most direct testable interpretation of
that seasonal demand asymmetry: winter heating-demand-driven withdrawals
should on average be associated with firmer/more volatile-to-the-upside
natural gas prices than the comparatively placid injection season, so being
long UNG (natural gas ETF proxy) only during the Nov-Mar withdrawal window
should outperform being long UNG unconditionally or during the Apr-Oct
injection window. First natural-gas-storage-cycle-specific calendar strategy
in this repo (prior UNG/natural-gas KB hits, if any, used different
mechanics).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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
    withdrawal_start_month: int = 11,
    withdrawal_end_month: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long during the withdrawal season (calendar months from
    withdrawal_start_month through withdrawal_end_month, wrapping around
    year-end, e.g. Nov-Mar by default); flat during the injection season
    (the remaining months, e.g. Apr-Oct by default).
    """
    df = _prep(price_df)
    months = df.index.month

    if withdrawal_start_month <= withdrawal_end_month:
        in_withdrawal = (months >= withdrawal_start_month) & (months <= withdrawal_end_month)
    else:
        # wraps around year-end (e.g. Nov(11) -> Mar(3))
        in_withdrawal = (months >= withdrawal_start_month) | (months <= withdrawal_end_month)

    position = pd.Series(in_withdrawal.astype(int), index=df.index)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)
    position = generate_signals(price_df, **kwargs)
    # shift position by 1 to avoid lookahead: today's return earned by
    # yesterday's end-of-day position
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
