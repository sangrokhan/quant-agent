"""Strategy: SP500 Down-Week weekly mean-reversion (buy after a down week, hold one week).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-19-064):
Per QuantifiedStrategies.com's "SP500 Down Week Trading Strategy (SPY)"
(https://www.quantifiedstrategies.com/sp500-down-week-trading-strategy/,
May 2025), a fully-disclosed rule: check the weekly close -- if SPY's
closing price on Friday is lower than the previous Friday's closing
price (a "down week"), buy at that Friday's close; hold exactly one
week, exit at the following Friday's close; only enter a new trade after
another down week. Source's own backtest (SPY, full history): 0.44%
avg gain/trade, 9.3% CAGR (vs 10.4% buy-and-hold), 36% max drawdown
(vs 55% buy-and-hold), 42% time invested -- a lower-risk, lower-return
alternative to buy-and-hold via a weekly mean-reversion filter.

First strategy in this repo using a WEEKLY-CLOSE-vs-PRIOR-WEEKLY-CLOSE
comparison as the entry trigger with a fixed one-week hold -- distinct
from all other calendar/day-of-week strategies already tested
(Turnaround Tuesday/Wednesday use daily percentage-drop gates within a
week; Monday-buy/Friday-sell 2026-09-04-106 is an unconditional weekly
hold gated by trend+volatility-range, not a down-week trigger; OPEX/
Triple-Witching are event-calendar-based, not price-based).

Adapted from the source's implicit "always hold for the down-week
signal" rule to a {0,1} position series usable on daily bars: identify
each week's last trading day (Friday, or the last trading day of the
week if Friday is a holiday), compare its close to the prior week's
last-trading-day close, and hold long for exactly the following week
(from the signal day's close through the next week's last-trading-day
close) whenever a down week is detected.

Signal logic
------------
- Resample close to weekly (W-FRI) to get each week's closing price
  and the corresponding last trading day within that week.
- down_week[w] = close[w] < close[w-1] (this week's close below last
  week's close).
- On a down week, go long from that week's last trading day's close
  through the NEXT week's last trading day's close (source's "hold for
  one week" rule).
- No new entry starts until the current hold completes (source's
  "repeat: only enter a new trade after another down week" -- since
  the hold IS exactly one week, this is automatically satisfied by the
  weekly resampling: a fresh down-week decision is only made once per
  week, at each week's own close).
- Long-only; flat between down-week signals.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def generate_signals(
    price_df: pd.DataFrame,
    week_freq: str = "W-FRI",
    min_decline_pct: float = 0.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    ``week_freq`` controls the weekly-close anchor day (default Friday,
    per the source article; can be varied as a grid-sensitivity check).
    ``min_decline_pct`` is an OPTIONAL magnitude filter beyond the
    source's bare "any decline" trigger (source's own rule is
    min_decline_pct=0.0, i.e. ANY down week qualifies) -- set > 0 to
    require at least that fractional weekly decline (e.g. 0.01 = 1%)
    before triggering, filtering out very shallow/noisy down-weeks.
    """
    df = _prep(price_df)
    close = df["close"]

    # Map each trading day to its containing week's period, then find
    # each week's LAST actual trading day (handles holidays shortening
    # a week) and that day's close.
    week_period = close.index.to_period(week_freq.replace("W-", "W-"))
    last_day_per_week = close.groupby(week_period).apply(lambda s: s.index[-1])
    week_close = close.groupby(week_period).last()

    weekly_pct_change = week_close.pct_change()
    down_week = (weekly_pct_change < -min_decline_pct).fillna(False)

    position = pd.Series(0, index=close.index)
    week_index_list = list(week_close.index)
    for i, wk in enumerate(week_index_list):
        if not down_week.loc[wk]:
            continue
        if i + 1 >= len(week_index_list):
            continue  # no next week to hold through in this sample
        entry_day = last_day_per_week.loc[wk]
        next_wk = week_index_list[i + 1]
        exit_day = last_day_per_week.loc[next_wk]
        # Long from entry_day (exclusive, since position is applied via
        # shift(1) in generate_returns) through exit_day (inclusive).
        mask = (close.index > entry_day) & (close.index <= exit_day)
        position.loc[mask] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    week_freq: str = "W-FRI",
    min_decline_pct: float = 0.0,
) -> pd.Series:
    """Return the strategy's daily return series."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(df, week_freq=week_freq, min_decline_pct=min_decline_pct)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
