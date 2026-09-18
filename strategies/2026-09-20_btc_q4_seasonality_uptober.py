"""Strategy: Bitcoin Q4 seasonality ("Uptober"/"Rektember") -- long ONLY
during October-November-December, flat all other months.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-011):
Per The Motley Fool (Dominic Basulto, Sep 12 2026,
https://www.fool.com/investing/2026/09/12/september-has-historically-been-a-difficult-month/)
citing long-run Bitcoin historical monthly-return statistics: September is
BTC's worst calendar month by a wide margin (avg return -2.93%, nicknamed
"Rektember" by long-time crypto traders), while October ("Uptober", avg
+20%), November (avg +41%), and December (avg +4%) are BTC's strongest
months. Corroborated independently by CoinDesk (Oct 2025: "Since 2013,
bitcoin has averaged 14.4% gains in October, with a median return of 10.8%
... 10 of 13 Octobers ended in the green") and multiple other sources
(Blockearner/TrustWallet citing +21.89% avg October return 2013-2024).

This is distinct from this repo's existing single-month-exclusion equity
strategy (2026-09-12_september_avoidance_seasonality.py, SPY-focused,
"stay out of September only, invested every other month") in two ways:
(1) it is BTC/crypto-native rather than an equity-market study applied
to crypto as a falsification check, and (2) the hypothesis is a much
NARROWER positive-carry window (ONLY Oct/Nov/Dec long, flat the other 9
months) rather than "long everywhere except one excluded month" -- testing
whether Bitcoin's return distribution is concentrated enough in this
specific 3-month window that a narrow seasonal hold beats both buy-and-hold
and the broader September-exclusion construction.

First BTC-monthly-seasonality (Q4-concentration) strategy in this repo.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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
    hold_months: tuple = (10, 11, 12),
    trend_window: int = 0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long only during calendar months in `hold_months` (default Oct/Nov/Dec);
    flat every other month. Optional `trend_window`: if > 0, additionally
    require close above its own trend_window-day SMA to stay long during a
    qualifying month (robustness check on top of the raw calendar effect;
    set to 0 to test the pure unconditional seasonal rule as the sources
    themselves report it).
    """
    df = _prep(price_df)
    close = df["close"]

    months = pd.Series(df.index.month, index=df.index)
    calendar_long = months.isin(set(hold_months))

    if trend_window and trend_window > 0:
        sma = close.rolling(trend_window).mean()
        trend_ok = (close > sma).fillna(False)
        position = (calendar_long & trend_ok).astype(int)
    else:
        position = calendar_long.astype(int)

    return position


def generate_returns(
    price_df: pd.DataFrame,
    hold_months: tuple = (10, 11, 12),
    trend_window: int = 0,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs here)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        hold_months=hold_months,
        trend_window=trend_window,
    )

    daily_returns = close.pct_change().fillna(0.0)
    # Execution-lag convention: trade on yesterday's signal.
    strat_returns = position.shift(1).fillna(0) * daily_returns
    return strat_returns
