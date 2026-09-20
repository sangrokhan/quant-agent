"""Strategy: Even-vs-odd calendar-day-of-month parity effect.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-165):
Per QuantifiedStrategies.com's "Even Vs. Odd Days Trading Strategy"
(https://www.quantifiedstrategies.com/even-vs-odd-days-trading-strategy-backtest-sp-500/),
S&P 500 gains historically concentrate disproportionately on EVEN
calendar-day-of-month dates rather than ODD ones: buying the close of an
odd calendar day and holding to the close of the next even calendar day
outperformed the mirror-image odd-day-holding strategy, though most of the
outperformance accrued after the 2008 financial crisis and the source
itself flags the effect as plausibly a random artifact rather than a
genuine structural edge (no disclosed causal mechanism -- unlike
day-of-week effects tied to settlement/payroll flows). This strategy
operationalizes the disclosed "buy on odd calendar day close, hold to next
even calendar day close" (long_parity="even") rule as a testable,
mechanical, walk-forward-checkable hypothesis, honestly logging outcome
regardless of the source's own randomness caveat.

Signal logic
------------
- Each trading day is classified by its actual calendar day-of-month
  (1-31) as odd or even.
- If long_parity == "even": go long (hold) starting at the close of a day
  classified ODD, exit at the close of the next day classified EVEN
  (i.e. we are "in the trade" overnight from an odd-day close to the
  following even-day close, capturing what the source calls "even day"
  performance since the payoff accrues while the calendar reads even the
  next morning -- matching the source's own definition literally: "At the
  close of odd days, we buy... hold... until close of following even day.
  This is the performance of even days.")
- If long_parity == "odd": mirror image (long from an even-day close to
  the next odd-day close).
- No position is held across a same-parity day (e.g. two odd days with no
  even day between them due to weekends/holidays skip cleanly -- the
  position from the day after an odd trading day is exited on the next
  trading day that is classified with the target parity).
- Flat otherwise (this is a fully invested/flat oscillation, not a
  continuous holding -- so day gaps over weekends are naturally captured
  since we use the trading calendar's actual dates, not a fixed N-day
  cycle).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _daily_position(daily_dates: pd.DatetimeIndex, long_parity: str) -> pd.Series:
    """Compute the {0,1} daily-resolution position series described above,
    operating on one row per CALENDAR DAY (daily_dates must be unique/sorted).
    """
    day_of_month = pd.Series(daily_dates.day, index=daily_dates)
    is_target_close_day = (day_of_month % 2 == 0) if long_parity == "even" else (day_of_month % 2 == 1)
    is_entry_close_day = ~is_target_close_day

    position = pd.Series(0, index=daily_dates, dtype=int)
    in_position = False
    for i in range(len(daily_dates)):
        if in_position:
            position.iloc[i] = 1
            if is_target_close_day.iloc[i]:
                in_position = False
        else:
            position.iloc[i] = 0
            if is_entry_close_day.iloc[i]:
                in_position = True
    return position


def generate_signals(
    price_df: pd.DataFrame,
    long_parity: str = "even",
) -> pd.Series:
    """Return a {0,1} long/flat position series, aligned to price_df's own
    bar frequency (works for daily OR sub-daily/hourly bars -- the calendar
    parity is computed once per CALENDAR DAY and then forward-filled across
    intraday bars, since this is fundamentally a daily-resolution calendar
    effect, not an intraday one).

    long_parity: "even" -> hold from an odd-calendar-day close to the next
        even-calendar-day close (source's disclosed "even day performance"
        rule). "odd" -> mirror image.
    """
    df = _prep(price_df)
    idx = df.index

    # One row per calendar day, in original bar order.
    cal_day = idx.normalize()
    unique_days = pd.DatetimeIndex(sorted(set(cal_day)))
    daily_pos = _daily_position(unique_days, long_parity=long_parity)

    # Forward-fill the once-per-day position across all intraday bars of
    # that same day (for daily-bar data this is a 1:1 mapping already).
    position = pd.Series(daily_pos.reindex(cal_day).to_numpy(), index=idx)
    return position.astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    long_parity: str = "even",
) -> pd.Series:
    """Strategy returns at price_df's own bar frequency (no transaction
    costs applied here)."""
    df = _prep(price_df)
    close = df["close"]
    bar_ret = close.pct_change().fillna(0.0)

    position = generate_signals(price_df, long_parity=long_parity)
    # Position decided using info as-of the PRIOR bar's close (no lookahead):
    # shift by one bar before applying to this bar's return.
    strat_ret = bar_ret * position.shift(1).fillna(0)
    return strat_ret
