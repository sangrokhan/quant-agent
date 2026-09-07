"""Strategy: Overnight-return premium capture, gated by a trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-053):
Per Bespoke Investment Group data (via marketrebellion.com): since 1993,
buying the S&P 500 at the close and selling at the next day's open (holding
ONLY overnight, flat during the intraday session) has produced dramatically
larger cumulative returns than the reverse (buying at the open, selling at
the close) -- ~1100% vs <100% cumulative. This is an unconditional
overnight-return-premium finding (no parameters in the source), so this
strategy makes it testable/tunable by adding a trend filter: only capture
the overnight return when in an established uptrend (close above a rolling
SMA), on the theory the premium is a compensated-risk phenomenon
concentrated in favorable regimes, not a pure calendar anomaly. First
overnight-return-premium construction in this repo (0 prior hits).

Signal logic
------------
- Overnight return for day t = open[t] / close[t-1] - 1 (position entered at
  the PRIOR day's close, exited at the current day's open -- flat during the
  intraday session).
- Trend filter: close[t-1] > SMA(trend_window) as of t-1 (known before the
  overnight hold decision).
- Position[t] = 1 (hold overnight into day t) iff the trend filter is
  satisfied as of close[t-1]; else 0 (stay in cash, no intraday exposure at
  all in either branch since this strategy structurally never holds
  intraday).
- No explicit exit/max-hold logic needed -- each day's overnight hold is a
  fresh independent decision (this is a repeated single-day-holding-period
  strategy, not a multi-day position).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
        Returns the overnight-only daily return series (0 on days the trend
        filter is off, open/prior_close - 1 on days it's on).
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0,1} series: 1 = held an overnight position INTO that
        bar's open (i.e. entered at the prior close).
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
    trend_window: int = 50,
) -> pd.Series:
    """Return a {0,1} series: 1 = holding overnight into this bar's open."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(trend_window).mean()
    trend_up = close > sma
    # Decision to hold overnight INTO bar t is made using info known as of
    # the PRIOR close (t-1): shift the trend filter forward by 1 bar.
    position = trend_up.shift(1).fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Overnight-only daily returns: open[t]/close[t-1] - 1, gated by trend filter."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]

    position = generate_signals(price_df, **kwargs)
    overnight_ret = (open_ / close.shift(1) - 1.0).fillna(0.0)
    strategy_ret = position * overnight_ret
    return strategy_ret
