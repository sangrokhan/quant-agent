"""Strategy: Bollinger Band mean reversion, SMA(200) trend-gated, with exit
at the UPPER Bollinger Band (not the middle basis) to let winners run.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per a r/algotrading post ("Surviving 2008 and 2022 with a 10% Drawdown: A
20-Year ETF Mean Reversion Study", u/vaanam-dev, read via browser_exec
Google-SERP fallback -- web_search DDGS backend TLS-erroring on multiple
queries this iteration): entry when close crosses below the lower 20-day
Bollinger Band (2 std) AND close > SMA(200) (uptrend filter, avoids
"catching falling knives" in a crash); exit when close crosses above the
UPPER Bollinger Band (not the middle basis line). The source's own
disclosed finding: switching the exit target from the middle band to the
upper band (letting the mean-reversion trade ride the full snap-back
rather than taking profit early at the middle) turned a mediocre 2.44%
CAGR/12.89% MDD result into a 7.22% CAGR/15.24% MDD result on SPY
(single-ETF backtest, 2006-2025, frictionless).

This repo already has a similar SMA(200)-gated Bollinger mean-reversion
strategy in strategies/2026-09-03_bb_meanrev_qqq_volregime.py, but that one
(a) gates on a realized-vol-regime filter, not a raw SMA(200) level filter,
and (b) exits at the MIDDLE band (basis SMA) or on a vol-regime flip/time-
stop, never the upper band. This strategy isolates the source's specific
claimed improvement -- swapping the exit target to the upper band -- as
its own standalone, directly comparable test.

Signal logic
------------
- 20-day SMA basis, 20-day std, bb_std multiplier (source: 2.0).
- Lower band = basis - bb_std*std; Upper band = basis + bb_std*std.
- Entry (long): close < lower_band AND close > SMA(trend_window) (source:
  200).
- Exit: close > upper_band, OR a max_hold_days safety-valve time-stop
  (source has no time-stop; added per this repo's convention to bound
  worst-case holding period given the source's own observed longest-trade
  of 400 calendar days).
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position).
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
    bb_window: int = 20,
    bb_std: float = 2.0,
    trend_window: int = 200,
    max_hold_days: int = 120,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    basis = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()
    lower_band = basis - bb_std * std
    upper_band = basis + bb_std * std

    trend_ok = close > close.rolling(trend_window).mean()
    entry = (close < lower_band) & trend_ok.fillna(False)
    exit_signal = close > upper_band

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]) if pd.notna(entry.iloc[i]) else False:
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
    strategy_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strategy_ret
