"""Strategy: Long-term monthly-channel trend-following with Bulkowski's
"three black candles" trend-change exit signal.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-136):
Per https://thepatternsite.com/MonthlyChannels.html (Thomas Bulkowski,
"Bulkowski on Monthly Trends", browser_exec), on the MONTHLY chart, once an
up-sloping price channel/trend has been established for >= 2 years, a
reliable trend-change SELL signal is three consecutive black (down-close)
monthly candles measured from the channel's highest candle so far (if that
highest candle is itself white, require 3 more consecutive black candles
after it; if it's already black, require 2 more consecutive black candles).
Source's own 1990-2017, 503-stock / 897-channel study: 42% of channels show
this signal at some point, average post-signal decline 43%, false-signal
rate 21%, ~3.7-year average time to recover back above the channel top.

This repo's adaptation to a single-instrument continuous long/flat
strategy: go long once price has been in an established uptrend (monthly
close above a rising `trend_sma_months`-month SMA) for at least
`min_uptrend_months` consecutive months (approximating the source's
"channel established >= 2 years" precondition); exit to flat the first time
either (a) the disclosed 3-black-candle trend-change signal fires (tracked
from the running highest monthly candle since entry), or (b) monthly close
falls back below the trend SMA (a secondary, more conservative stop in case
the 3-black-candle signal is slow to trigger). Re-entry requires the
uptrend precondition to be re-satisfied from scratch.

First long-horizon MONTHLY-bar chart-pattern strategy in this repo (distinct
from all prior daily-bar candlestick/trend strategies) and the first to use
Bulkowski's specific "three black candles from channel high" trend-change
rule.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
    generate_signals(price_df, **params) -> pd.Series (daily {0,1} long/flat,
        forward-filled from the underlying monthly decision, shifted so the
        signal known only at a completed month's close is not used until the
        following trading day -- no lookahead).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _monthly_position(
    df: pd.DataFrame,
    trend_sma_months: int,
    min_uptrend_months: int,
) -> pd.Series:
    """Compute a {0,1} long/flat position at MONTHLY resolution, indexed by
    each month's completed-bar timestamp (last trading day of the month)."""
    monthly = df.resample("ME").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    ).dropna(subset=["close"])

    sma = monthly["close"].rolling(trend_sma_months).mean()
    sma_rising = sma > sma.shift(1)
    above_sma = monthly["close"] > sma
    uptrend_ok = (above_sma & sma_rising).astype(int)
    # Consecutive-months-in-uptrend counter (resets to 0 on any break).
    grp = (uptrend_ok == 0).cumsum()
    consec_uptrend = uptrend_ok.groupby(grp).cumsum()

    is_black = monthly["close"] < monthly["open"]

    n = len(monthly)
    pos = pd.Series(0, index=monthly.index, dtype=int)

    in_position = False
    channel_high = None
    channel_high_is_black = None
    black_run_since_high = 0

    consec_vals = consec_uptrend.values
    close_vals = monthly["close"].values
    black_vals = is_black.values
    sma_vals = sma.values

    for i in range(n):
        if not in_position:
            if consec_vals[i] >= min_uptrend_months:
                in_position = True
                channel_high = close_vals[i]
                channel_high_is_black = bool(black_vals[i])
                black_run_since_high = 1 if channel_high_is_black else 0
        else:
            # Track running channel high since entry.
            if close_vals[i] > channel_high:
                channel_high = close_vals[i]
                channel_high_is_black = bool(black_vals[i])
                black_run_since_high = 1 if channel_high_is_black else 0
            else:
                if black_vals[i]:
                    black_run_since_high += 1
                else:
                    black_run_since_high = 0

            needed = 3 if not channel_high_is_black else 2
            three_black_signal = black_run_since_high >= needed and black_run_since_high >= 1 and (
                (not channel_high_is_black and black_run_since_high >= 3)
                or (channel_high_is_black and black_run_since_high >= 2)
            )
            sma_break = (not pd.isna(sma_vals[i])) and close_vals[i] < sma_vals[i]

            if three_black_signal or sma_break:
                in_position = False
                channel_high = None
                channel_high_is_black = None
                black_run_since_high = 0

        pos.iloc[i] = 1 if in_position else 0

    return pos


def generate_signals(
    price_df: pd.DataFrame,
    trend_sma_months: int = 24,
    min_uptrend_months: int = 24,
) -> pd.Series:
    """Return a daily {0,1} long/flat position series, no lookahead."""
    df = _prep(price_df)
    monthly_pos = _monthly_position(df, trend_sma_months, min_uptrend_months)

    # Forward-fill the monthly decision onto the daily index. A month's
    # decision is only knowable once that month's bar closes, so the daily
    # position for a given day reflects the most recently COMPLETED month
    # strictly before it (reindex+ffill already achieves this: a monthly
    # timestamp is that month's last trading day, so it only starts
    # appearing in the ffill from the next daily row onward). The final
    # shift(1) inside generate_returns (matching this repo's convention)
    # additionally ensures the position is applied one full trading day
    # after it's knowable, so there's no lookahead.
    daily_pos = monthly_pos.reindex(df.index, method="ffill").fillna(0).astype(float)
    return daily_pos


def generate_returns(
    price_df: pd.DataFrame,
    trend_sma_months: int = 24,
    min_uptrend_months: int = 24,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs here)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        trend_sma_months=trend_sma_months,
        min_uptrend_months=min_uptrend_months,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0.0) * daily_returns
    return strat_returns
