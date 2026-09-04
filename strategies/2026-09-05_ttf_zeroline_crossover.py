"""Strategy: Trend Trigger Factor (TTF) zero-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-015):
The Trend Trigger Factor (TTF, M.H. Pee, Technical Analysis of Stocks &
Commodities, Dec 2004) compares "buying power" and "selling power" over
two adjacent n-bar windows (the current n bars vs. the prior n bars) to
gauge directional pressure. Per Stonehill Forex's disclosure of the
original TASC formula: Buy Power = Highest High of the current n-bar
window minus Lowest Low of the prior n-bar window; Sell Power = Highest
High of the prior n-bar window minus Lowest Low of the current n-bar
window; TTF = 100 * (Buy Power - Sell Power) / (0.5 * (Buy Power + Sell
Power)). The stated mechanical rule: TTF crossing above the zero line is
a long entry (executed next bar open, simplified here to same-bar
close); TTF crossing below zero is the exit/short signal.

First TTF strategy in this repo -- same author (M.H. Pee) as Trend
Intensity Index (id=2026-09-04-123, sums signed SMA deviations, already
rejected) and Random Walk Index (id=2026-09-04-153), but TTF's
buy-power/sell-power extremes-differencing construction is structurally
distinct from both.

Formula (exact, per original TASC/Stonehill Forex disclosure):
  BP_t = HH(close_high, t-n+1..t) - LL(close_low, t-2n+1..t-n)
  SP_t = HH(close_high, t-2n+1..t-n) - LL(close_low, t-n+1..t)
  TTF_t = 100 * (BP_t - SP_t) / (0.5 * (BP_t + SP_t))

Signal logic
------------
- Entry (long): TTF crosses above 0.
- Exit: TTF crosses below 0, OR a max_hold_days time-stop backstop
  (source notes TTF is commonly used as a "confirmation" indicator
  layered on a baseline system; standalone here it needs its own exit
  discipline, hence the time-stop).
- Flat otherwise.

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


def _ttf(high: pd.Series, low: pd.Series, n: int) -> pd.Series:
    hh_current = high.rolling(n, min_periods=n).max()
    ll_current = low.rolling(n, min_periods=n).min()
    hh_prior = hh_current.shift(n)
    ll_prior = ll_current.shift(n)

    buy_power = hh_current - ll_prior
    sell_power = hh_prior - ll_current

    denom = 0.5 * (buy_power + sell_power)
    ttf = 100.0 * (buy_power - sell_power) / denom.replace(0.0, pd.NA)
    return ttf


def generate_signals(
    price_df: pd.DataFrame,
    n: int = 8,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    close = df["close"]

    ttf = _ttf(high, low, n)

    above_zero = ttf > 0
    cross_up = above_zero & (~above_zero.shift(1).fillna(False))
    cross_down = (~above_zero) & above_zero.shift(1).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(cross_down.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = position.shift(1).fillna(0) * close.pct_change().fillna(0.0)
    return daily_ret
