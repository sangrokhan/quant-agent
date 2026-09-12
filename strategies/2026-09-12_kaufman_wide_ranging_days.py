"""Strategy: Perry Kaufman "Wide Ranging Days" candle pattern (ATR-confirmed
outside day), trend-filtered fixed-holding-period breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-12-193):
Per Perry Kaufman's S&C January 2021 "New Rules for a New Market" article,
covered at https://financial-hacker.com/petra-on-programming-short-term-
candle-patterns/ (fully disclosed C code): "Wide Ranging Days" is an
Outside Day pattern (higher high AND lower low than the prior bar, close
in the upper or lower 25% of the day's range) additionally gated by a
volatility-expansion condition -- today's True Range must exceed 1.5x the
20-day ATR. This differs from the already-tested Key Reversal (2026-09-12-
191, REJECTED decisively) by requiring the close to land in the extreme
quartile of TODAY's own range (not necessarily beyond yesterday's high/low)
AND by requiring genuine volatility expansion (TR > 1.5*ATR(20)) as a
confirming filter -- Kaufman's own rationale being that an outside day
without above-average range expansion is a weaker, more common, and less
informative signal.

Source's own methodology: fixed 1-5 day holding period test with/without
an SMA trend filter across a multi-asset basket, framed as an open
empirical question rather than a proven edge. This iteration operationalizes
the bullish-only variant with an SMA trend filter, giving it a genuine
test in this repo's validator framework (distinct params from Key Reversal:
this strategy's core gate is the ATR expansion multiplier, not a raw
outside-day-plus-close-beyond-prior-range condition).

Signal logic
------------
- Outside day: high[t] > high[t-1] AND low[t] < low[t-1].
- Wide-range gate: TrueRange[t] > atr_mult * ATR(atr_window)[t].
- Bullish close-quartile gate: close[t] falls in the UPPER 25% of today's
  own [low[t], high[t]] range, i.e. close[t] > low[t] + 0.75*(high[t]-low[t]).
- Trend filter: close[t] above its own trailing `trend_sma_window`-day SMA.
- Entry: all four conditions true on the same bar.
- Exit: fixed `hold_days`-day holding period (source's own literal
  methodology), no other exit condition.

Interface contract for validators (see validation/validators.py) and
grid_test (see validation/grid_test.py):
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        {0, 1} position series aligned to price_df.index.
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
        Daily strategy returns (position-weighted, no transaction costs
        applied here).

Tunable params (all keyword args, per RESEARCH_LOOP.md Step 5 contract):
    atr_window       (ATR lookback, default 20, source's literal value).
    atr_mult         (True Range must exceed this multiple of ATR, default
        1.5, source's literal value).
    trend_sma_window (default 80, matches Key Reversal's default for
        comparability).
    hold_days        (fixed holding period, default 3).
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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.rolling(window, min_periods=window).mean()
    return tr, atr


def generate_signals(
    price_df: pd.DataFrame,
    atr_window: int = 20,
    atr_mult: float = 1.5,
    trend_sma_window: int = 80,
    hold_days: int = 3,
) -> pd.Series:
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    prev_high = high.shift(1)
    prev_low = low.shift(1)
    outside_day = (high > prev_high) & (low < prev_low)

    tr, atr = _atr(df, atr_window)
    wide_range = tr > (atr_mult * atr)

    day_range = (high - low).replace(0.0, np.nan)
    upper_quartile = close > (low + 0.75 * day_range)

    sma = close.rolling(trend_sma_window, min_periods=trend_sma_window).mean()
    trend_ok = close > sma

    entry_signal = (outside_day & wide_range & upper_quartile & trend_ok).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    hold_remaining = 0
    for i in range(len(close)):
        if hold_remaining > 0:
            position.iloc[i] = 1
            hold_remaining -= 1
        elif entry_signal.iloc[i]:
            position.iloc[i] = 1
            hold_remaining = hold_days - 1
        else:
            position.iloc[i] = 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    atr_window: int = 20,
    atr_mult: float = 1.5,
    trend_sma_window: int = 80,
    hold_days: int = 3,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        atr_window=atr_window,
        atr_mult=atr_mult,
        trend_sma_window=trend_sma_window,
        hold_days=hold_days,
    )
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
