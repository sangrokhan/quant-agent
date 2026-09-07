"""Strategy: Ehlers Instantaneous Trendline (iTrend) reversed mean-reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-005):
Per https://www.elitetrader.com/et/threads/john-ehlers-trading-strategy-the-instantaneous-trendline-backtest.374341/
(quantifiedstrategies.com backtest of Ehlers' Instantaneous Trendline,
Stocks & Commodities Jan 2006), the textbook trend-following rule (go long
when ITrend crosses ABOVE its own 1-bar-lagged value) performed "disastrous"
on both ES-mini futures and SPY, in- and out-of-sample. But REVERSING the
signal direction -- go long when ITrend crosses BELOW its own lagged value
(i.e. treat the standard "sell" signal as a mean-reversion buy trigger,
exploiting SPY's bullish drift/buy-the-dip bias) -- with a short dominant-
cycle-length parameter (they optimized to period=2) and a price-action exit
turned it into a strategy the source reports beat buy-and-hold: 1009 trades
since 1993, 10.56% annual return vs 7.72% buy-and-hold, 65.71% win rate,
45.51% time invested, 23.96% max drawdown vs 56.47% buy-and-hold (no
dividends/commissions). We reproduce the REVERSED rule using the standard
simplified fixed-alpha Ehlers Instantaneous Trendline formula (2-pole
recursive filter, alpha=2/(period+1), as popularized in Ehlers' "Rocket
Science for Traders") since the source did not disclose their exact exit
rule -- we use a symmetric exit (ITrend crosses back above its lag) plus a
max_hold_days time-stop as our own reasonable substitute for their
undisclosed "price action-based exit criterion". First Ehlers Instantaneous
Trendline strategy in this repo.

Signal logic
------------
- price = (high + low) / 2.
- alpha = 2 / (period + 1).
- ITrend[t] = (alpha - alpha^2/4)*price[t] + 0.5*alpha^2*price[t-1]
              - (alpha - 0.75*alpha^2)*price[t-2]
              + 2*(1-alpha)*ITrend[t-1] - (1-alpha)^2*ITrend[t-2]
  (seeded with price for the first few bars, per the standard formula).
- Entry (long, REVERSED per source's own optimization finding): ITrend
  crosses BELOW its own 1-bar-lagged value (this bar's ITrend < ITrend[-1],
  previous bar's ITrend >= ITrend[-2]) -- i.e. the textbook "sell" signal
  used instead as a contrarian buy trigger.
- Exit: ITrend crosses back ABOVE its 1-bar-lagged value (mirror signal),
  OR a max_hold_days time-stop (our own substitute for the source's
  undisclosed price-action exit).
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series   ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
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


def _itrend(price: pd.Series, period: int) -> pd.Series:
    alpha = 2.0 / (period + 1)
    p = price.to_numpy()
    n = len(p)
    it = np.zeros(n)
    for i in range(n):
        if i < 3:
            it[i] = p[i]
        else:
            it[i] = (
                (alpha - alpha ** 2 / 4.0) * p[i]
                + 0.5 * alpha ** 2 * p[i - 1]
                - (alpha - 0.75 * alpha ** 2) * p[i - 2]
                + 2.0 * (1 - alpha) * it[i - 1]
                - (1 - alpha) ** 2 * it[i - 2]
            )
    return pd.Series(it, index=price.index)


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 2,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close, high, low = df["close"], df["high"], df["low"]
    price = (high + low) / 2.0 if "high" in df.columns and "low" in df.columns else close

    itrend = _itrend(price, period)
    itrend_lag = itrend.shift(1)

    below_now = itrend < itrend_lag
    below_prev = below_now.shift(1).fillna(False)
    entry = below_now & (~below_prev)  # cross from above/equal to below (reversed signal)
    entry = entry.fillna(False)

    above_now = itrend > itrend_lag
    above_prev = above_now.shift(1).fillna(False)
    exit_cross = above_now & (~above_prev)
    exit_cross = exit_cross.fillna(False)

    n = len(df)
    entry_arr = entry.to_numpy()
    exit_arr = exit_cross.to_numpy()
    pos_arr = [0] * n

    in_pos = False
    hold_counter = 0
    for i in range(n):
        if in_pos:
            hold_counter += 1
            exit_now = bool(exit_arr[i]) or hold_counter >= max_hold_days
            if exit_now:
                in_pos = False
                hold_counter = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if bool(entry_arr[i]):
                in_pos = True
                hold_counter = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    period: int = 2,
    max_hold_days: int = 10,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(price_df, period=period, max_hold_days=max_hold_days)
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
