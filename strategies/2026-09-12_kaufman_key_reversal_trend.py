"""Strategy: Perry Kaufman "Key Reversal" candle pattern, trend-filtered.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-12-191):
Per Perry Kaufman's S&C January 2021 "New Rules for a New Market" article,
covered at https://financial-hacker.com/petra-on-programming-short-term-
candle-patterns/ (fully disclosed C code): "Key Reversal" -- a higher high
AND a lower low than the prior bar (i.e. today's range engulfs
yesterday's), with today's close breaking OUTSIDE yesterday's range: close
below yesterday's low = bearish signal, close above yesterday's high =
bullish signal. This differs from a plain outside-day/engulfing pattern by
requiring the close itself (not just the range) to have broken the prior
bar's extreme, i.e. an outside-day bar that closes at a fresh extreme
rather than mid-range.

Source's own methodology: test each candle pattern on a basket of assets
with a fixed holding period (1-5 days) and optionally an SMA trend filter,
reporting via a results table rather than a single accept/reject verdict
-- the source explicitly frames this as an open empirical question, not a
proven edge (echoing the source's own skeptical framing: "it seems no one
yet got rich with them"). This iteration operationalizes the bullish-only
variant with the source's own optional trend filter (price above/below a
trailing SMA) as a genuinely testable mechanical strategy for this repo's
validator suite, rather than reusing the source's flat/no-filter framing
verbatim.

Signal logic
------------
- Key Reversal bullish signal on day t: high[t] > high[t-1] AND
  low[t] < low[t-1] (outside day) AND close[t] > high[t-1] (closed above
  yesterday's high, not just inside the wider range).
- Trend filter (source's own "WithTrend" option): only take the signal if
  close[t] is above its own trailing `trend_sma_window`-day SMA (uptrend
  context) -- per source's script structure (`vars Trend =
  series(SMA(seriesC(),80))`).
- Entry: long on a qualifying bullish Key Reversal bar (trend-filtered).
- Exit: after `hold_days` trading days (source's own fixed-holding-period
  methodology, tested with day 1-5 in the original article) -- no other
  exit condition, matching the source's literal test design.

Interface contract for validators (see validation/validators.py) and
grid_test (see validation/grid_test.py):
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        {0, 1} position series aligned to price_df.index.
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
        Daily strategy returns (position-weighted, no transaction costs
        applied here).

Tunable params (all keyword args, per RESEARCH_LOOP.md Step 5 contract):
    trend_sma_window (default 80, source's own literal example value).
    hold_days (fixed holding period after entry, default 3, mid-range of
        source's tested 1-5 day sweep).
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


def generate_signals(
    price_df: pd.DataFrame,
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
    key_reversal_bull = outside_day & (close > prev_high)

    sma = close.rolling(trend_sma_window, min_periods=trend_sma_window).mean()
    trend_ok = close > sma

    entry_signal = (key_reversal_bull & trend_ok).fillna(False)

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
    trend_sma_window: int = 80,
    hold_days: int = 3,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = generate_signals(price_df, trend_sma_window=trend_sma_window, hold_days=hold_days)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
