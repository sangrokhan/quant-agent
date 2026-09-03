"""Strategy: Crypto weekend effect (long Friday close through Monday close).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-029):
Per QuantifiedStrategies.com's Bitcoin weekend-effect article
(https://www.quantifiedstrategies.com/weekend-effect-in-bitcoin/):
Bitcoin (and other crypto, a 24/7 market unlike stocks) tends to show
positive price movement from late Friday through late Monday, attributed
to reduced institutional weekend trading volume/liquidity and increased
retail-driven activity. Source's own (paywalled/undisclosed exact rules)
premium strategy backtest: BTC 103 trades, avg gain 2.6%/trade, win rate
60%, MDD 19%, only 10% time invested, risk-adjusted return 280%; ETH 64
trades, avg gain 2.2%/trade, win rate 53%, MDD 30%. This is the first
crypto-NATIVE calendar anomaly tested in this repo (distinct from every
prior calendar strategy -- day-of-week Tuesday 2026-09-03-018, pre-holiday
gap-detector 2026-09-03-020, turn-of-month 2026-09-03-006 -- which were
all designed for stocks' weekday-only trading calendar and are trivially
inapplicable to a 24/7 market). Since the source's exact entry/exit HOURS
are paywalled, this implements the qualitative rule literally: long from
Friday's daily close through Monday's daily close (holding through
Saturday and Sunday, no weekend market closure to work around on crypto).

Signal logic
------------
- Determine each bar's day-of-week (Mon=0 ... Sun=6) from the index.
- Position = 1 on Friday, Saturday, and Sunday bars (captures Saturday's,
  Sunday's, and Monday's daily returns via the standard 1-day
  position-lag convention used by generate_returns).
- Flat (0) on Monday through Thursday.
- On equity data (weekday-only trading calendar, no Sat/Sun bars), this
  strategy is trivially near-zero-signal (only the Friday bar itself ever
  triggers a position, and equity markets have no Sat/Sun close to
  capture) -- expected and consistent with the mechanism being
  crypto-native.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
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
    entry_weekday: int = 4,  # Friday (0=Mon ... 6=Sun)
    hold_days: int = 3,  # hold through Fri, Sat, Sun bars
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    weekday = pd.Series(close.index, index=close.index).apply(lambda ts: ts.weekday())

    hold_weekdays = {(entry_weekday + i) % 7 for i in range(hold_days)}
    position = weekday.isin(hold_weekdays).astype(int)
    position.index = close.index
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
