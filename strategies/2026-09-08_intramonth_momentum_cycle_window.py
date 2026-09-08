"""Strategy: Intramonth Momentum Cycle Window (calendar-timed momentum).

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD):
Per Nathan, Suominen & Tasa, "The Intramonth Momentum Cycle" (SSRN 2026,
summarized via Google SERP snippets and StockViz's replication write-up at
https://stockviz.biz/2026/07/18/intramonth-momentum/, and its sector-ETF
extension "Sectoral Intramonth Momentum Cycle" at
https://quantpedia.com/sectoral-intramonth-momentum-cycle-exploiting-turn-of-the-month-patterns-in-sector-etf-strategies/):
U.S. equity momentum returns concentrate almost entirely in a narrow
6-trading-day window each month, ENDING 4 trading days before month-end
(i.e. momentum's edge decays/reverses in the final days approaching
month-end, consistent with turn-of-month rebalancing flows -- also
discussed in this repo's already-tested turn-of-month and rebalancing-
pressure entries -- temporarily overwhelming the momentum signal). This
strategy times a simple absolute-momentum (trailing `lookback_months`-month
return sign) long/flat position to be ACTIVE ONLY during that specific
intramonth window (a `window_days`-trading-day block ending `end_offset`
trading days before month-end), flat all other days -- rather than holding
the momentum position unconditionally every day as this repo's existing
GEM-style dual-momentum strategies do (2026-09-04-097, 2026-09-07 SPY/TLT
and SPY/IEF variants). First strategy in this repo to gate a momentum
signal to a specific INTRAMONTH trading-day-count window (distinct from
turn-of-month calendar-boundary strategies, which gate to a window
STRADDLING the month boundary itself, e.g. 2026-09-06-169, 2026-09-05-072).

Signal logic
------------
- trading_days_to_month_end[t] = count of trading days remaining in t's
  calendar month as of bar t (0 = last trading day of the month).
- window[t] = True iff end_offset <= trading_days_to_month_end[t] <
  end_offset + window_days (a `window_days`-day block ending `end_offset`
  trading days before month-end).
- momentum_signal[t] = close[t] / close[t - lookback_months*21] - 1 > 0
  (simple absolute momentum via a ~21-trading-day-per-month proxy).
- Position[t] = 1 iff window[t-1] AND momentum_signal[t-1] (decision known
  as of prior close, shifted forward 1 bar); else 0.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _trading_days_to_month_end(index: pd.DatetimeIndex) -> pd.Series:
    """For each bar, count of trading days remaining in its calendar month
    (0 = last trading day of the month, per the actual trading calendar)."""
    ym = pd.Series(list(zip(index.year, index.month)), index=index)
    result = pd.Series(0, index=index, dtype=int)
    for key, group_idx in ym.groupby(ym).groups.items():
        n = len(group_idx)
        # last element -> 0, first element -> n-1
        result.loc[group_idx] = list(range(n - 1, -1, -1))
    return result


def generate_signals(
    price_df: pd.DataFrame,
    lookback_months: int = 12,
    window_days: int = 6,
    end_offset: int = 4,
) -> pd.Series:
    """Return a {0,1} series: 1 = long during the intramonth momentum window."""
    df = _prep(price_df)
    close = df["close"]

    lookback_bars = lookback_months * 21
    momentum_signal = (close.pct_change(lookback_bars) > 0).fillna(False)

    days_to_month_end = _trading_days_to_month_end(df.index)
    window = (days_to_month_end >= end_offset) & (days_to_month_end < end_offset + window_days)

    raw_signal = window & momentum_signal
    position = raw_signal.shift(1).fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Close-to-close returns while holding the intramonth momentum window position."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(price_df, **kwargs)
    asset_ret = close.pct_change().fillna(0.0)
    strategy_ret = position * asset_ret
    return strategy_ret
