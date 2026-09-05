"""Strategy: Turn-of-the-Month (TOTM) with a "Tactical Twist" short-term-weakness filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-072):
The plain Turn-of-the-Month calendar effect was already tested and rejected
in this repo (2026-09-03-006, SPY Sharpe 0.98 near-miss). Per
QuantifiedStrategies.com's "The Turn-of-the-Month Effect - With a Tactical
Twist" article (June 2026) plus its own Instagram/social promo snippet
("...turn of the month when price is showing short-term weakness... take
trades [when] close [is] below [a] moving average... Across 167 trades, the
strategy produced a 67% win rate"; the article itself confirms SPY, 167
trades, 1.2% avg gain/trade, 67% win ratio, profit factor 2.8, 6% CAGR, 14%
exposure, 15% MDD -- the precise numeric entry/exit thresholds are
paywalled), the "tactical twist" only takes the TOTM long entry when price
is ALSO showing short-term weakness (close below a short moving average)
going into the window -- i.e. requiring a pullback/dip WITHIN the seasonal
window, rather than trading the window unconditionally. This should reduce
trade frequency/exposure (source reports only 14% time-in-market vs the
plain TOTM window's larger exposure) and filter out TOTM occurrences where
price is already extended, plausibly improving the risk-adjusted return
that the plain TOTM near-missed on.

Signal logic
------------
- TOTM window: last `days_before_month_end` trading day(s) of the month
  plus the first `days_after_month_start` trading days of the next month
  (same window definition as 2026-09-03-006's plain TOTM).
- Tactical twist filter: close < SMA(weakness_window) on the day the window
  begins (short-term weakness/pullback precondition).
- Entry (long): TOTM window is active AND the weakness filter was true at
  the window's start (checked once per window-entry, held for the
  window's duration -- not re-checked every day inside the window).
- Exit: TOTM window ends (flat on all non-window days), or immediately if
  entry criteria failed.

Interface contract (RESEARCH_LOOP.md Step 5):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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
    days_before_month_end: int = 1,
    days_after_month_start: int = 3,
    weakness_window: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    idx = df.index
    close = df["close"]
    ym = pd.Series(idx.year * 100 + idx.month, index=idx)

    rank_from_start = ym.groupby(ym).cumcount()
    rank_from_end = ym.groupby(ym).cumcount(ascending=False)

    near_month_end = rank_from_end < days_before_month_end
    near_month_start = rank_from_start < days_after_month_start
    totm_window = (near_month_end | near_month_start)

    sma = close.rolling(weakness_window).mean()
    weak = close < sma

    # window_start = first day of a contiguous TOTM window block.
    window_start = totm_window & ~totm_window.shift(1).fillna(False)

    position = pd.Series(0, index=idx, dtype=int)
    active = False
    for i in range(len(idx)):
        if bool(window_start.iloc[i]):
            active = bool(totm_window.iloc[i]) and bool(weak.iloc[i])
        elif not bool(totm_window.iloc[i]):
            active = False
        position.iloc[i] = 1 if (active and bool(totm_window.iloc[i])) else 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
