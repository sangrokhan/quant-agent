"""Strategy: 5-Day Low of the Range (IBS + N-day lowest-low breakdown),
mean reversion, trend-gated.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-011):
Per QuantifiedStrategies.com's "The 5-Day Low of The Range Strategy"
article (https://www.quantifiedstrategies.com/5-day-low-of-the-range-strategy/,
read via browser_exec after web_search DDGS/Yahoo backend errored with TLS
RequestError on this iteration's queries): the article discloses the
combined entry criterion in plain English -- IBS (Internal Bar Strength =
(Close-Low)/(High-Low)) lower than 0.25 AND today's close lower than the
lowest low of the previous 5 days -- as producing an edge that "far
exceeds the average return for any 5-day period" on SPY since 1993 (309/
517 winners full-period; more recent 102-trade subsample: 68 winners,
0.98% avg return/trade). The exact numeric exit/holding rule is paywalled,
so this implementation uses the article's own disclosed reference point
(profitability peaks 3-7 days, "exiting after five days" as the discussed
holding horizon) as a fixed max_hold_days exit, plus an IBS-recovery exit
(close moves back toward the top of its range) as an early-exit condition,
both gated by a 200-day SMA uptrend filter (the same trend-confirmation
pattern already validated for other IBS-family strategies in this repo).

This is a NEW combined-condition construction, distinct from every prior
IBS-family entry in this repo (2026-09-04-089 simple IBS threshold-cross,
2026-09-04-158/159 N-day averaged IBS, 2026-09-04-164 Rob Hanna
"Adjusted Failed Bounce" which requires *high* prior-day IBS in a downtrend
continuation setup) -- here LOW same-day IBS is combined with an N-day
lowest-low breakdown as a joint oversold-panic signal, not a bounce-failure
or averaged-IBS pattern.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position series).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _ibs(df: pd.DataFrame) -> pd.Series:
    rng = (df["high"] - df["low"]).replace(0.0, float("nan"))
    return (df["close"] - df["low"]) / rng


def generate_signals(
    price_df: pd.DataFrame,
    ibs_entry_threshold: float = 0.25,
    ibs_exit_threshold: float = 0.75,
    low_lookback: int = 5,
    trend_window: int = 200,
    max_hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ibs = _ibs(df)
    trend_up = close > close.rolling(trend_window).mean()
    prior_lowest_low = df["low"].shift(1).rolling(low_lookback).min()

    entry_cond = (ibs < ibs_entry_threshold) & (close < prior_lowest_low) & trend_up
    ibs_recovery_exit = ibs > ibs_exit_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(ibs_recovery_exit.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_cond.iloc[i]):
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
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
