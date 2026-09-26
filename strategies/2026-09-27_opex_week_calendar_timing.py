"""Strategy: Option-Expiration (OPEX) Week calendar timing.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-001):
Per Quantpedia's "Option-Expiration Week Effect"
(https://quantpedia.com/strategies/option-expiration-week-effect, free,
sourced from Stivers & Sun "Returns and Option Activity over the
Option-Expiration Week for S&P 100 Stocks", SSRN 1571786) and corroborated
by QuantifiedStrategies.com's "The Options Expiration Week Effect - OPEX
Seasonality" (https://quantifiedstrategies.substack.com/p/the-options-expiration-week-effect-e2a,
free Google-cache snippet -- disclosed rule: "buys on the open of the
options expiration week and exits on the close of the options expiration
day (usually a Friday)"): large-cap, actively-optioned stocks show
abnormally high average weekly returns during the option-expiration week
(the week containing the 3rd Friday of each month), driven by option
market-maker delta-hedge rebalancing as near-term options approach
expiration. A simple market-timing strategy: go long at the open of the
Monday starting OPEX week, hold through the close of the 3rd Friday, flat
the rest of the month. Quantpedia's own source-paper backtest (1988-2010,
S&P 100 universe): Sharpe 0.61, ~9.3% p.a., MDD -15.14%.

This is the FIRST OPEX/3rd-Friday-week calendar-timing strategy in this
repo (distinct from Turn-of-Month, Turnaround Tuesday, Santa Claus Rally,
and other calendar-seasonality entries already tested -- none anchor on
the monthly options-expiration cycle specifically).

Mechanically infeasible on crypto (no monthly options-expiration cycle
analogous to equity index options), so this hypothesis is equity-only by
construction; the grid test still runs the crypto leg per the standard
grid-test procedure to formally confirm this expectation (a flat/no-signal
result is the correct, informative outcome there, not an error).

Signal logic
------------
- Determine, for each trading day, the calendar month's 3rd Friday (the
  standard US equity/index monthly-options-expiration day). "OPEX week" is
  defined as the block of trading days from (and including) the Monday of
  that calendar week through (and including) that 3rd Friday itself.
- Long (position=1) on every trading day that falls within an OPEX week;
  flat otherwise.
- No stop-loss / no time-stop (entries and exits are calendar-driven, not
  price-driven, matching the source's own construction).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
"""

from __future__ import annotations

import calendar

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _third_friday(year: int, month: int):
    """Return the date of the 3rd Friday of the given calendar month."""
    cal = calendar.monthcalendar(year, month)
    fridays = [week[calendar.FRIDAY] for week in cal if week[calendar.FRIDAY] != 0]
    return pd.Timestamp(year=year, month=month, day=fridays[2])


def generate_signals(
    price_df: pd.DataFrame,
    hold_extra_days: int = 0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    hold_extra_days: optional extension of the OPEX window backward (in
    calendar days before the 3rd Friday) beyond the strict Monday-Friday
    week, to test sensitivity of the window definition (default 0 = exact
    Quantpedia/source definition: Monday of 3rd-Friday week through 3rd
    Friday itself).
    """
    df = _prep(price_df)
    idx = df.index
    close = df["close"]

    # Build the set of (start, end) OPEX-window date ranges spanning the
    # data's date range, with a 1-month buffer on each side.
    dates = pd.DatetimeIndex(idx.normalize().unique())
    if len(dates) == 0:
        return pd.Series(0, index=idx, dtype=int)

    start_year, start_month = dates.min().year, dates.min().month
    end_year, end_month = dates.max().year, dates.max().month

    tz = idx.tz  # match the price index's tz-awareness (naive or UTC etc.)

    def _localize(ts: pd.Timestamp) -> pd.Timestamp:
        return ts.tz_localize(tz) if tz is not None else ts

    windows = []
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        third_fri = _third_friday(y, m)
        week_start = third_fri - pd.Timedelta(days=third_fri.weekday())  # Monday of that week
        window_start = week_start - pd.Timedelta(days=hold_extra_days)
        windows.append((_localize(window_start), _localize(third_fri)))
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1

    position = pd.Series(0, index=idx, dtype=int)
    day_norm = idx.normalize()
    for w_start, w_end in windows:
        mask = (day_norm >= w_start) & (day_norm <= w_end)
        position.loc[mask] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    # OPEX week is known in advance (calendar-driven, not lagged/lookahead
    # since the calendar dates are known ex-ante), but still shift by 1 to
    # stay consistent with this repo's standard "trade on next bar"
    # execution convention used across all other strategies here.
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
