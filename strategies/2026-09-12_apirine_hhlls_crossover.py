"""Strategy: Apirine Higher High / Lower Low Stochastic (HHLLS) crossover
with 50-line confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-12-194):
Per Vitali Apirine's S&C February 2016 "Higher Highs & Lower Lows" article
(TASC 34:02, fully disclosed MetaStock code, PDF text-extracted directly):
two momentum stochastics --

  HS[t] = (High[t] - LowestHigh(20)) / (HighestHigh(20) - LowestHigh(20))
          if High[t] > High[t-1] else 0
  LS[t] = (HighestLow(20) - Low[t]) / (HighestLow(20) - LowestLow(20))
          if Low[t] < Low[t-1] else 0
  HHS = 20-day EMA of HS * 100
  LLS = 20-day EMA of LS * 100

Source's own disclosed "emerging trend" rule (two-stage): stage 1 = HHS
crosses above LLS (new higher-highs are more recent than new lower-lows);
stage 2 = HHS moves above 50 AND LLS moves below 50 (bulls have the edge).
Source notes the two stages don't always occur in the same order. This
strategy operationalizes the FULL two-stage rule as the entry condition
(both conditions true simultaneously, since requiring only the crossover
without the 50-level confirmation risks earlier/weaker signals per
source's own emerging-trend discussion), exiting on the mirror bearish
signal (LLS crosses above HHS, or LLS>50 while HHS<50).

This is architecturally distinct from every existing "higher high / lower
low" strategy in this repo (ZigZag pivot HH+HL breakout structures,
Bulkowski Outside Day continuation, two-bar Inside-Day-then-Outside-Day
DIA pattern) since HHLLS is a smoothed MOMENTUM STOCHASTIC pair (EMA of a
bounded 0-100 ratio, tracking how *fresh* recent extremes are, not a raw
swing-pivot or single-bar range pattern), and distinct from the
already-tested Correlation Trend Indicator (2026-09-08-033, Pearson
correlation vs. a straight line) and R-squared trend-quality gate
(2026-09-07-004) as a wholly different mathematical construction (highest/
lowest-high normalized ratio, not correlation/regression).

Signal logic
------------
- Long entry: HHS > LLS AND HHS > 50 AND LLS < 50 (source's full two-stage
  emerging-uptrend confirmation).
- Exit (flatten): LLS > HHS OR (LLS > 50 AND HHS < 50) (mirror bearish
  condition per source's own symmetric framing).
- Otherwise carry forward previous position.

Interface contract for validators (see validation/validators.py) and
grid_test (see validation/grid_test.py):
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        {0, 1} position series aligned to price_df.index.
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
        Daily strategy returns (position-weighted, no transaction costs
        applied here).

Tunable params (all keyword args, per RESEARCH_LOOP.md Step 5 contract):
    lookback_window (default 20, source's literal value, used for both the
        highest/lowest-high/low lookback AND the EMA smoothing period, per
        source's own literal design where both share the same "20-day"
        parameter).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _hhlls(df: pd.DataFrame, lookback_window: int):
    high = df["high"]
    low = df["low"]

    prev_high = high.shift(1)
    prev_low = low.shift(1)

    lowest_high = high.rolling(lookback_window, min_periods=lookback_window).min()
    highest_high = high.rolling(lookback_window, min_periods=lookback_window).max()
    highest_low = low.rolling(lookback_window, min_periods=lookback_window).max()
    lowest_low = low.rolling(lookback_window, min_periods=lookback_window).min()

    hh_range = (highest_high - lowest_high).replace(0.0, np.nan)
    hs_raw = (high - lowest_high) / hh_range
    hs = hs_raw.where(high > prev_high, 0.0)

    ll_range = (highest_low - lowest_low).replace(0.0, np.nan)
    ls_raw = (highest_low - low) / ll_range
    ls = ls_raw.where(low < prev_low, 0.0)

    hs = hs.fillna(0.0)
    ls = ls.fillna(0.0)

    hhs = hs.ewm(span=lookback_window, adjust=False).mean() * 100.0
    lls = ls.ewm(span=lookback_window, adjust=False).mean() * 100.0

    return hhs, lls


def generate_signals(
    price_df: pd.DataFrame,
    lookback_window: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    hhs, lls = _hhlls(df, lookback_window)

    bullish = (hhs > lls) & (hhs > 50) & (lls < 50)
    bearish = (lls > hhs) | ((lls > 50) & (hhs < 50))

    position = pd.Series(0, index=close.index, dtype=int)
    pos = 0
    warmup = lookback_window
    for i in range(len(close)):
        if i < warmup:
            position.iloc[i] = 0
            continue
        if bullish.iloc[i]:
            pos = 1
        elif bearish.iloc[i]:
            pos = 0
        position.iloc[i] = pos

    return position


def generate_returns(
    price_df: pd.DataFrame,
    lookback_window: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = generate_signals(price_df, lookback_window=lookback_window)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
