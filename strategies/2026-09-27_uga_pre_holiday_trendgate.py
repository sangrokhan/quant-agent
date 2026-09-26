"""Strategy: Pre-Holiday Effect in Commodities, trend-gated (UGA D-5->D-1 + SMA filter).

Direct rescue of this same cron trigger's prior rejection 2026-09-27-016
(UGA pre-holiday D-5->D-1 hold, Sharpe 0.983 near-miss, all other
validators passed cleanly incl. relative_std=0.042 parameter stability).
Per that entry's own filed rescue idea: add a trend/momentum pre-filter to
avoid taking the pre-holiday trade during a strong prevailing downtrend in
crude/gasoline (source article itself notes "the most significant
drawdown [was] in the months leading to the 2022 Russian invasion of
Ukraine" -- an unfiltered downtrend period). This is a self-constructed
refinement (not from a new external source this iteration -- pure
parameter/filter follow-up on 2026-09-27-016's own diagnostic, per
RESEARCH_LOOP.md Step 3 "record novelty judgment" allowance for direct
fixes of a same-trigger near-miss).

Signal logic
------------
Identical D-5->D-1 holiday-anchored entry/exit as
2026-09-27_uso_uga_pre_holiday_effect.py, gated by an additional trend
filter evaluated at D-5 (the entry decision date): only take the trade if
close(D-5) > SMA(trend_window) computed as of D-5. If the filter fails,
skip that holiday's window entirely (flat).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1})
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _holiday_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    cal = USFederalHolidayCalendar()
    start = index.min() - pd.Timedelta(days=30)
    end = index.max() + pd.Timedelta(days=30)
    return cal.holidays(start=start, end=end)


def generate_signals(
    price_df: pd.DataFrame,
    entry_days_before: int = 5,
    trend_window: int = 50,
) -> pd.Series:
    df = _prep(price_df)
    idx = df.index
    close = df["close"]
    sma = close.rolling(trend_window).mean()

    position = pd.Series(0, index=idx, dtype=int)
    trading_days = idx.normalize()

    holidays = _holiday_dates(idx)
    for h in holidays:
        before = trading_days[trading_days < h]
        if len(before) < entry_days_before:
            continue
        pos_d1 = idx.get_indexer([before[-1]])[0]
        pos_entry = pos_d1 - (entry_days_before - 1)
        if pos_entry < 0:
            continue
        # Trend filter evaluated at the entry decision point (D-5's close).
        entry_close = close.iloc[pos_entry]
        entry_sma = sma.iloc[pos_entry]
        if pd.isna(entry_sma) or entry_close <= entry_sma:
            continue  # skip this holiday window: not in an uptrend

        lo = pos_entry + 1
        hi = pos_d1 + 1
        if lo < hi:
            position.iloc[lo:hi] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    entry_days_before: int = 5,
    trend_window: int = 50,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, entry_days_before=entry_days_before, trend_window=trend_window)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position * daily_ret
    return strategy_ret.fillna(0.0)
