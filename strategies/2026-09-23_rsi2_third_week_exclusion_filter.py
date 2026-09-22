"""Strategy: RSI(2) mean-reversion with a THIRD-CALENDAR-WEEK-OF-MONTH exclusion filter.

Hypothesis (see knowledge_base/strategies_log.jsonl, this iteration's id):
Per StatOasis's "RSI Deep Dive: How to Trade the S&P 500 Like a Pro with Mean
Reversion" (Ali Casey, https://statoasis.com/overfit/research/rsi-deep-dive-
how-to-trade-the-sp500-like-a-pro-with-mean-reversion), a 146,880-combination
grid search over RSI(2) mean-reversion parameters found the single most
robust configuration to be: Entry RSI(2) < 25, Exit RSI(2) > 65 or after a
fixed 5-bar time-stop. The source separately reports that adding a TIME
FILTER -- specifically avoiding new trade entries during the THIRD calendar
week of the month -- reduced noise/risk exposure (net profit degraded only
slightly, from $236,662 to $231,975, while exposure/time-in-market dropped
meaningfully to 29.8%, i.e. fewer, cleaner trades for similar profit).

This repo already has 10+ RSI(2)/Connors-family variants (see
knowledge_base/strategies_index.jsonl), but NONE of them apply a
within-month CALENDAR-WEEK exclusion filter -- every prior RSI(2) entry/exit
tweak has varied the oscillator construction, trend gate, or exit mechanic,
never a pure calendar-timing overlay on top of the plain RSI(2) rule. This
strategy isolates that specific novel angle: identical RSI(2) entry/exit
mechanic to the already-accepted baseline (2026-09-03-005) plus a
close>SMA(200) uptrend filter (standard construction used throughout this
repo's RSI(2) family, not explicitly restated by the source but implicit in
its "market regime filter" discussion), with NEW ENTRIES suppressed whenever
the bar falls in the third ISO calendar week of the month.

Signal logic
------------
- RSI(2) via Wilder's method on the traded asset's own close.
- Trend gate: close > SMA(trend_window) (default 200).
- Calendar gate: a bar's day-of-month determines its "week of month"
  (week = ((day - 1) // 7) + 1, so days 15-21 are week 3 by this bucketing,
  matching the source's own casual "third week of the month" framing).
  NEW ENTRIES are suppressed when the CURRENT bar falls in week 3 of its
  month -- an existing open position may still be exited on schedule
  regardless of calendar week (only entries are gated, per the source's own
  framing of this as noise/risk reduction on new trade initiation).
- Long entry: RSI(2) crosses to a value < entry_threshold (25) AND
  close > SMA(trend_window) AND NOT third-week-of-month.
- Exit: RSI(2) > exit_threshold (65) OR exit_bars (5) trading days have
  elapsed since entry (whichever comes first) OR the trend filter breaks
  (close <= SMA(trend_window), safety backstop not explicit in the source
  but consistent with this repo's established RSI(2) trend-gate pattern).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _wilder_rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(avg_loss != 0, 100.0)
    rsi = rsi.where(avg_gain != 0, 0.0)
    return rsi


def _week_of_month(index: pd.DatetimeIndex) -> pd.Series:
    day = index.day
    week = ((day - 1) // 7) + 1
    return pd.Series(week, index=index)


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 2,
    entry_threshold: float = 25.0,
    exit_threshold: float = 65.0,
    exit_bars: int = 5,
    trend_sma: int = 200,
    exclude_week: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series from the RSI(2) + third-week-exclusion filter."""
    df = _prep(price_df)
    close = df["close"]

    rsi = _wilder_rsi(close, rsi_period)
    sma = close.rolling(trend_sma, min_periods=trend_sma).mean()
    uptrend = close > sma

    wom = _week_of_month(df.index)
    entry_allowed_calendar = wom != exclude_week

    valid = rsi.notna() & sma.notna()

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    bars_held = 0

    for i in range(len(close)):
        if not bool(valid.iloc[i]):
            position.iloc[i] = 0
            continue

        if in_position:
            bars_held += 1
            exit_signal = (
                bool(rsi.iloc[i] > exit_threshold)
                or bars_held >= exit_bars
                or not bool(uptrend.iloc[i])
            )
            if exit_signal:
                in_position = False
                bars_held = 0
            position.iloc[i] = 1 if in_position else 0
        else:
            entry_signal = (
                bool(rsi.iloc[i] < entry_threshold)
                and bool(uptrend.iloc[i])
                and bool(entry_allowed_calendar.iloc[i])
            )
            if entry_signal:
                in_position = True
                bars_held = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    rsi_period: int = 2,
    entry_threshold: float = 25.0,
    exit_threshold: float = 65.0,
    exit_bars: int = 5,
    trend_sma: int = 200,
    exclude_week: int = 3,
) -> pd.Series:
    """Return daily strategy returns (position held from signal close to next bar close)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        rsi_period=rsi_period,
        entry_threshold=entry_threshold,
        exit_threshold=exit_threshold,
        exit_bars=exit_bars,
        trend_sma=trend_sma,
        exclude_week=exclude_week,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(int) * daily_returns
    return strat_returns
