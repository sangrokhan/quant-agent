"""Strategy: ChartMill Trend Indicator (CTI) weekly long-only trend-follow.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per ChartMill.com's own documentation
(https://www.chartmill.com/documentation/technical-analysis/indicators/32-The-ChartMill-Trend-Indicator-(CTI)),
the ChartMill Trend Indicator classifies each WEEK as positive, negative, or
neutral relative to a 30-week EMA:

    - positive: week's LOW is above a RISING 30-week EMA, and the 30-week
      EMA has been rising for >= 3 consecutive weeks.
    - negative: week's HIGH is below a DECLINING 30-week EMA, and the
      30-week EMA has been declining for >= 3 consecutive weeks.
    - neutral: otherwise.

The source's own worked SPY example (10-year chart) shows the indicator
tracking major bull/bear regimes (positive 1996-2000, negative 2000-2003,
positive 2003-2007, negative 2008-Mar2009, positive post-Mar2009) with very
few whipsaws -- a slow, low-frequency, uncomplicated trend filter, in
contrast to this repo's many faster oscillator-crossover strategies.

This iteration's test: go long daily bars whenever the (resampled) weekly
CTI state is positive; go flat whenever it's neutral or negative. No
separate time-stop -- position simply tracks the weekly regime state
directly (same "regime state, no discrete trigger" pattern already used
successfully for e.g. the accepted Laguerre-RSI zero-line regime filter,
2026-09-06-110), applied here to price/EMA-slope persistence rather than an
oscillator threshold.

First ChartMill/CTI-family strategy in this repo (zero prior matches for
"ChartMill"/"CTI" in strategies_index.jsonl) and the first weekly-resampled
regime-state strategy tested in this loop's history, distinct from the
existing purely-daily trend filters (SMA/EMA slope, ADX, Hurst, etc.).

Source: https://www.chartmill.com/documentation/technical-analysis/indicators/32-The-ChartMill-Trend-Indicator-(CTI)
(exact rule fully and freely disclosed, no paywall).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _weekly_cti(
    df: pd.DataFrame, ema_period: int = 30, rising_weeks: int = 3
) -> pd.Series:
    """Compute the weekly ChartMill Trend Indicator state (+1/0/-1),
    indexed by the last trading day of each week (W-FRI)."""
    weekly = df.resample("W-FRI").agg(
        {"high": "max", "low": "min", "close": "last"}
    ).dropna()

    ema30 = weekly["close"].ewm(span=ema_period, adjust=False).mean()
    ema_diff = ema30.diff()

    rising = ema_diff > 0
    declining = ema_diff < 0
    rising_streak = rising.rolling(rising_weeks).sum() == rising_weeks
    declining_streak = declining.rolling(rising_weeks).sum() == rising_weeks

    positive = (weekly["low"] > ema30) & rising_streak
    negative = (weekly["high"] < ema30) & declining_streak

    state = pd.Series(0, index=weekly.index, dtype=int)
    state[positive] = 1
    state[negative] = -1
    return state


def generate_signals(
    price_df: pd.DataFrame,
    ema_period: int = 30,
    rising_weeks: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series (daily index)."""
    df = _prep(price_df)
    close = df["close"]

    weekly_state = _weekly_cti(df, ema_period=ema_period, rising_weeks=rising_weeks)
    # Forward-fill the weekly state onto the daily index. Shift the weekly
    # state's own index by 0 -- reindexing with ffill naturally means a given
    # daily bar only sees weekly states known as of that week's close (no
    # look-ahead: a week's own CTI value is only knowable once fully
    # observed, so we align on the week-ending Friday timestamp already used
    # as the resample label, and the daily generate_returns() shift(1)
    # handles same-day-close look-ahead avoidance on top of this).
    daily_state = weekly_state.reindex(close.index, method="ffill")

    position = (daily_state == 1).astype(int).fillna(0)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
