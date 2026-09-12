"""Strategy: 7-day momentum signal, held ONLY during weekend calendar days
(crypto, 24/7 market).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-13-020):
Per Kumari, Wasan & Chhimwal (2025) "The Weekend Effect in Crypto Momentum:
Does Momentum Change When Markets Never Sleep?" (Advances in Consumer
Research, https://acr-journal.com/article/the-weekend-effect-in-crypto-momentum-does-momentum-change-when-markets-never-sleep--1514/,
read via browser_exec this iteration), a 7-day-lookback momentum strategy
on 10 major cryptocurrencies (2020-2025) shows weekend (Sat-Sun UTC)
returns SIGNIFICANTLY exceed weekday returns for every coin tested
(p<0.05): e.g. BTC weekday mean daily return 0.0012 vs weekend 0.0023
(t=2.41, p=0.016), Sharpe 0.038 (weekday) vs 0.072 (weekend), MDD -0.28
(weekday) vs -0.18 (weekend) -- consistently better risk-adjusted
performance on weekends. The source's own strategy is long/short; this
repo's long-only adaptation (per SAFETY.md) tests: take the standard 7-day
momentum LONG signal (go long when trailing 7-day return is positive), but
only actually HOLD the position during weekend calendar days (Saturday and
Sunday UTC), staying flat on weekdays regardless of the momentum signal.
This is distinct from all 17 prior weekend/day-of-week entries in this
repo (which test either unconditional weekend calendar holds, or plain
day-of-week seasonality without a momentum signal) because it specifically
GATES A MOMENTUM SIGNAL to weekend days, testing whether the source's
finding that momentum itself performs differently on weekends translates
into an exploitable combined signal.

Signal logic
------------
- Momentum signal: trailing mom_lookback-day (default 7) simple return is
  positive.
- Weekend gate: the current bar's calendar day-of-week (UTC) is Saturday
  (5) or Sunday (6).
- Entry/hold (long): momentum signal positive AND current day is a
  weekend day.
- Flat: any weekday, or a weekend day with a non-positive momentum signal.
- No shorting (SAFETY.md) -- the source's short leg on negative momentum
  is dropped entirely.

Interface contract for validators (see validation/validators.py) and the
grid tester (see validation/grid_test.py): both generate_signals and
generate_returns accept price_df plus the strategy's tunable parameters as
keyword arguments. Crypto-primary hypothesis (24/7 market with real
weekend bars); also tested on equity as a falsification check (equity
loaders return weekday-only bars, so the weekend gate should produce an
all-flat/degenerate series there by construction).
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
    mom_lookback: int = 7,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    momentum = close.pct_change(mom_lookback)
    momentum_positive = (momentum > 0).fillna(False)

    is_weekend = df.index.dayofweek.isin([5, 6])
    is_weekend = pd.Series(is_weekend, index=df.index)

    position = (momentum_positive & is_weekend).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    mom_lookback: int = 7,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(price_df, mom_lookback=mom_lookback)

    daily_ret = close.pct_change().fillna(0.0)
    strat_returns = daily_ret * position.shift(1).fillna(0)
    return strat_returns
