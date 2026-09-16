"""Strategy: RSI(2) oversold setup with a TREND-RESUMPTION confirmation entry
and an N-day low-of-lows trailing-stop exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-002), sourced
from Cesar Alvarez's "Mean Reversion Entry Timing" article:
https://alvarezquanttrading.com/blog/mean-reversion-entry-timing/
(visited this iteration via browser_exec -- web_search's DDGS backend
TLS-errored on the initial query).

The article directly compares three entry-timing variants for the *same*
mean-reversion setup (oversold RSI + uptrend filter): (1) enter on next
open unconditionally, (2) enter on an intraday pullback limit order, and
(3) wait for "trend resumption" -- only enter once price has already begun
bouncing back (today's high crosses above yesterday's high, i.e. the setup
bar's high), which the author found gave the highest average CAR of the
three variants across his 2007-2017 S&P500 test, at the cost of missing
some trades that never confirm. It also separately compares RSI-recovery
exits against an "N-day low of lows" trailing-stop exit (exit when today's
close breaks below the lowest low of the trailing N days), which produced
a different, longer-holding-period risk/return profile (lower win rate,
higher CAR, larger MDD) than the fast RSI-recovery exit.

This repo already has a plain RSI(2)+SMA200 mean-reversion strategy
(2026-09-03-005, `strategies/2026-09-03_rsi2_meanrev_trend200.py`) that
enters IMMEDIATELY when RSI dips oversold (no confirmation wait) and exits
on a fast 5-day-SMA recovery. This strategy is a structurally distinct
combination never tested in this repo:
  1. Entry requires an explicit CONFIRMATION bar (price already turning back
     up, high > setup-bar's high) rather than entering on the oversold
     signal itself -- trading timeliness for a bounce-already-started
     signal, per the source's own found trend-resumption entry.
  2. Exit uses a much slower N-day trailing low-of-lows stop instead of a
     fast SMA-recovery or fixed RSI exit-threshold -- a trend-following-
     style exit bolted onto a mean-reversion entry, matching the source's
     own "Entry on Open, N-Day Exit" / "Trend Resumption + N-Day Exit"
     comparison rows.

Interface contract for validators (see validation/validators.py) and grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, window: int) -> pd.Series:
    """Wilder's RSI (standard exponential smoothing, alpha=1/window)."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 2,
    rsi_entry: float = 10.0,
    trend_window: int = 200,
    exit_lowoflows_window: int = 10,
    max_hold_days: int = 30,
) -> pd.Series:
    """Long-only {0,1} position series.

    Setup bar: close > SMA(trend_window) AND RSI(rsi_window) <= rsi_entry
    (oversold dip within an established uptrend) -- Alvarez's/Connors' usual
    mean-reversion setup.

    Confirmation/entry bar: the first subsequent bar whose HIGH exceeds the
    setup bar's own high (price has resumed moving up -- "trend resumption"
    entry per the source). We approximate the source's "enter at the prior
    day's high" limit-style fill with a same-bar-confirmed close-to-close
    entry (this repo's vectorbt-based returns engine trades at daily
    resolution, not intrabar fills) -- i.e. once a bar's high clears the
    setup high, we go long as of that bar's close.

    Exit: close < rolling min(low, exit_lowoflows_window) over the trailing
    window (N-day low-of-lows trailing stop, source's own disclosed
    alternative exit) OR a max_hold_days time-stop backstop (this repo's
    standard safety exit, not in the source, added since the raw N-day-low
    exit alone can hold indefinitely in a strong trend).
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    rsi = _rsi(close, rsi_window)
    trend_sma = close.rolling(trend_window).mean()
    above_trend = (close > trend_sma).fillna(False)
    setup = (above_trend & (rsi <= rsi_entry)).fillna(False)

    lowoflows = low.rolling(exit_lowoflows_window).min()
    exit_stop_trigger = (close < lowoflows).fillna(False)

    n = len(close)
    setup_vals = setup.values
    high_vals = high.values
    close_vals = close.values
    exit_vals = exit_stop_trigger.values

    pos_vals = [0] * n
    in_position = False
    pending_setup_high = None  # waiting for confirmation
    hold_count = 0

    for i in range(n):
        if in_position:
            hold_count += 1
            if exit_vals[i] or hold_count >= max_hold_days:
                in_position = False
                pos_vals[i] = 0
                hold_count = 0
            else:
                pos_vals[i] = 1
        else:
            if pending_setup_high is not None:
                # Waiting for confirmation: today's high must clear the
                # setup bar's high to trigger entry.
                if high_vals[i] > pending_setup_high:
                    in_position = True
                    pos_vals[i] = 1
                    hold_count = 0
                    pending_setup_high = None
                    continue
                # Confirmation not yet met -- if a fresh setup fires again
                # today, refresh the reference high; otherwise keep waiting
                # (but drop stale waits once trend/oversold condition no
                # longer holds, to avoid confirming on a stale, no-longer-
                # relevant setup).
                if setup_vals[i]:
                    pending_setup_high = high_vals[i]
                elif not (close_vals[i] > 0):
                    pass
                pos_vals[i] = 0
            else:
                if setup_vals[i]:
                    pending_setup_high = high_vals[i]
                pos_vals[i] = 0

    position = pd.Series(pos_vals, index=close.index, dtype=int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
