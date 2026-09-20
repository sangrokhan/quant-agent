"""Strategy: single-asset dynamic momentum/contrarian switching after a
sharp market plunge.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-183):
Per CXO Advisory's summary of Victoria Dobrynskaya's "Dynamic Momentum and
Contrarian Trading" (2017,
https://www.cxoadvisory.com/technical-trading/momentum-contrarian-equities-switching-strategy/),
a cross-sectional stock momentum hedge portfolio historically crashes not
during the month of a market plunge but during the following 1-3 months;
switching to a CONTRARIAN position for a few months right after a plunge
(instead of persisting with conventional momentum) turns those crash months
into gains. The source's own cross-sectional/long-short construction (long
winners, short losers, flipped after a plunge) doesn't map directly onto
this repo's single-asset, long-only contract, so this is adapted as a
single-asset TIME-SERIES absolute-momentum strategy:

- Conventional regime: long when trailing 12-1 month momentum (return from
  ~252 trading days ago to ~21 trading days ago) is positive, flat
  otherwise -- a standard absolute-momentum filter.
- Plunge detection: a monthly return more than `plunge_std_mult` (source's
  own baseline: 1.5) standard deviations below the trailing average monthly
  return triggers "plunge mode".
- Contrarian window: for `contrarian_months` (source's own baseline: 3)
  months starting one month (`lag_months`, source's own baseline: 1) after
  a detected plunge, the conventional momentum signal is INVERTED (i.e. go
  long when momentum is negative, flat when momentum is positive) --
  betting the recent panic-driven losers rebound rather than persisting
  with a losing conventional-momentum long.
- Outside the contrarian window, revert to the conventional absolute-
  momentum rule.

This is a genuinely new indicator family for this repo -- no prior entry
implements a regime-conditional signal INVERSION triggered by a
volatility-of-returns plunge detector.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series
        {0,1} position series aligned to price_df.index.
    generate_returns(price_df, **params) -> pd.Series
        Position-weighted daily returns (position shifted by 1 day to avoid
        look-ahead bias), no transaction costs applied here.
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
    momentum_lookback: int = 252,
    momentum_skip: int = 21,
    plunge_std_mult: float = 1.5,
    plunge_return_window: int = 21,
    lag_months_days: int = 21,
    contrarian_months_days: int = 63,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    # Conventional absolute (time-series) momentum: 12-1 month total return.
    momentum = (close.shift(momentum_skip) / close.shift(momentum_lookback)) - 1.0
    conventional_long = momentum > 0

    # Approximate "monthly" returns using a rolling window return series
    # (21 trading days ~= 1 month), then flag a plunge when that rolling
    # return is more than plunge_std_mult std devs below its own trailing
    # average.
    period_return = close.pct_change(plunge_return_window)
    trailing_mean = period_return.rolling(momentum_lookback, min_periods=plunge_return_window).mean()
    trailing_std = period_return.rolling(momentum_lookback, min_periods=plunge_return_window).std()
    plunge_flag = period_return < (trailing_mean - plunge_std_mult * trailing_std)
    plunge_flag = plunge_flag.fillna(False)

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    contrarian_start = -1
    contrarian_end = -1

    for i in range(n):
        if plunge_flag.iloc[i]:
            new_start = i + lag_months_days
            new_end = new_start + contrarian_months_days
            # Extend the active contrarian window if this plunge's window
            # reaches further than the current one.
            if new_end > contrarian_end:
                contrarian_start = new_start if contrarian_end < i else min(contrarian_start, new_start)
                contrarian_end = new_end

        conv = bool(conventional_long.iloc[i]) if not pd.isna(conventional_long.iloc[i]) else False
        if contrarian_start >= 0 and contrarian_start <= i <= contrarian_end:
            # Within the active contrarian window: invert conventional signal.
            position.iloc[i] = int(not conv) if not pd.isna(momentum.iloc[i]) else 0
        else:
            position.iloc[i] = int(conv)

    warmup = momentum_lookback + momentum_skip
    position.iloc[:warmup] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
