"""Strategy: Front-Run Seasonality (percentile-of-trailing-12mo, X-11 shift).

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id),
sourced from QuantPedia's "Trader's Guide to Front-Running Commodity
Seasonality" (https://vvv.quantpedia.com/traders-guide-to-front-running-commodity-seasonality/,
5 Dec 2024, Cyril Dujava, own-research, free -- web_extract failed with
"DuckDuckGo (ddgs) is a search-only backend and cannot extract URL content",
read via browser_exec fallback):

Naive time-series seasonality model (source's "Model 1"): at the end of
month t, predict whether to hold the asset during month t+1 by checking
whether that SAME calendar month's return exactly 12 months ago (month
t+1-12 = t-11) ranked in the top half of the trailing 12 monthly returns
ending at that lookback month. Source's own backtest (commodity sector
ETFs, 2007-2024): CAR -4.54%, Sharpe -0.40 -- i.e. NEGATIVE, because
"sophisticated market participants front-run the seasonal signal", so the
naive lookback is actually a REVERSED (contrarian) signal in practice.

Source's "Model 2" (the actual edge, what this file implements): shift the
lookback by ONE EXTRA month -- at the end of month t, use the return of
month t+2 (i.e. t-11 instead of t-12) from one year ago as the predictor
for whether to hold month t+1 this year. Source's own result: CAR +6.71%,
Sharpe 0.55, MaxDD -20.43%, vs Model 1's Sharpe -0.40/-MaxDD -60.26% on the
same 4 commodity ETFs (DBA/DBB/DBE/DBP, 2007-2024) -- a large,
directionally-flipped improvement from the single-month front-run shift.

This repo's single-asset simplification: the source's own methodology is
already "time-series" (each instrument judged against ITS OWN trailing-12mo
seasonality distribution, not cross-sectionally against sibling ETFs -- see
source's own explicit note distinguishing this from a cross-sectional
seasonality variant), so it translates directly to a single-symbol
long/flat filter without needing a multi-asset universe: go long the asset
for calendar month t+1 if the percentile rank of month (t+1-shift_months)
last year's return, among the trailing 12 monthly returns ending at that
lookback month, is >= percentile_threshold; flat otherwise. `shift_months`
default 11 reproduces source's front-run Model 2 (X-11); shift_months=12
reproduces source's reversed/negative-edge naive Model 1 for comparison.

First "front-run seasonality via percentile-rank-of-shifted-lookback-month"
strategy in this repo -- distinct from all prior calendar-seasonality
entries (Turn-of-Month, Sell-in-May, January Barometer, day-of-week, etc.)
which all use a fixed unconditional calendar window rather than a
per-instrument trailing-12-month percentile-rank predictor recomputed
every month.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
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


def _monthly_returns(close: pd.Series) -> pd.Series:
    """Month-end close-to-close returns, indexed by month-end Timestamp."""
    monthly_close = close.resample("ME").last()
    return monthly_close.pct_change()


def generate_signals(
    price_df: pd.DataFrame,
    shift_months: int = 11,
    lookback_window: int = 12,
    percentile_threshold: float = 0.5,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    For each calendar month t+1 (the month about to be entered), look up
    the return of month (t+1 - shift_months) from `lookback_window` months'
    history ending at that lookback month, rank it as a percentile within
    that trailing window, and go long month t+1 iff percentile >=
    percentile_threshold. shift_months=11 is the source's front-run
    ("Model 2"); shift_months=12 is the naive/reversed baseline ("Model 1").
    """
    df = _prep(price_df)
    idx = df.index
    close = df["close"]

    monthly_ret = _monthly_returns(close)  # indexed by month-end timestamp
    n = len(monthly_ret)

    # For each month-end index i (return realized IN that month, i.e.
    # monthly_ret.index[i] is month t, monthly_ret.iloc[i] is month t's
    # return), decide whether month (t+1) should be long, by looking at
    # lookback month = (t+1) - shift_months, i.e. index position:
    #   entry_month_idx = i + 1 (the month AFTER this month-end mark)
    #   lookback_idx = entry_month_idx - shift_months
    monthly_long_flag = pd.Series(0, index=monthly_ret.index, dtype=int)
    for i in range(n):
        entry_month_pos = i + 1  # position of the month we'd be entering
        lookback_pos = entry_month_pos - shift_months
        window_start = lookback_pos - (lookback_window - 1)
        if lookback_pos < 0 or window_start < 0 or lookback_pos >= n:
            continue
        window = monthly_ret.iloc[window_start: lookback_pos + 1]
        if window.isna().any() or len(window) < lookback_window:
            continue
        lookback_ret = monthly_ret.iloc[lookback_pos]
        percentile = (window <= lookback_ret).sum() / len(window)
        if percentile >= percentile_threshold:
            monthly_long_flag.iloc[i] = 1  # flag applies to the FOLLOWING month

    # Expand month-end flags to daily position: the flag set at month-end i
    # (computed using data through month i) determines the position for
    # all trading days within month (i+1).
    position = pd.Series(0, index=idx, dtype=int)
    month_periods = idx.to_series().dt.to_period("M")
    flag_by_period = {
        (monthly_ret.index[i] + pd.offsets.MonthEnd(1)).to_period("M"): monthly_long_flag.iloc[i]
        for i in range(n)
    }
    position_values = month_periods.map(flag_by_period).fillna(0).astype(int)
    position = pd.Series(position_values.values, index=idx, dtype=int)

    return position


def generate_returns(
    price_df: pd.DataFrame,
    shift_months: int = 11,
    lookback_window: int = 12,
    percentile_threshold: float = 0.5,
) -> pd.Series:
    """Daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        shift_months=shift_months,
        lookback_window=lookback_window,
        percentile_threshold=percentile_threshold,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_ret
