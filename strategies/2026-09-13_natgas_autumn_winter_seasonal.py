"""Strategy: Natural Gas (UNG) autumn pre-winter seasonal long window.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-13-XXX):
Per https://www.oildon.com/natural-gas-seasonal-patterns (read via
browser_exec this iteration), natural gas futures exhibit a well-known
storage-driven seasonal pattern: prices typically bottom in the spring
shoulder season (April-May), build a risk premium through the
September-October autumn shoulder ("pre-winter risk premium builds;
September skews bullish in seasonal studies") ahead of the November-March
withdrawal/heating season, and see their highest levels/volatility in
December-February. The source's own month-by-month table explicitly
flags September-October as bullish-skewed (building risk premium) and
December-February as highest-price (the culmination of that seasonal
run-up). This is the first Natural Gas / UNG strategy tested in this repo
(0 prior entries for this commodity/instrument).

Adapted here as a simple long-only seasonal calendar-window strategy on
UNG (a widely-tradable natural gas ETF, since raw Henry Hub futures aren't
obtainable via this repo's yfinance-only equity loader): long UNG from a
configurable start-of-window day of year (default day-of-year 250, ~early
September) through a configurable end-of-window day of year (default
day-of-year 45 of the FOLLOWING year, ~mid-February), spanning the
autumn-shoulder risk-premium build-up plus peak-winter period the source
describes; flat the rest of the year (spring/summer shoulder, when the
source describes prices as typically bottoming/range-bound).

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


def generate_signals(
    price_df: pd.DataFrame,
    window_start_doy: int = 250,
    window_end_doy: int = 45,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long when the calendar day-of-year is >= window_start_doy (wraps into
    the new year) OR <= window_end_doy -- i.e. a window that STRADDLES the
    calendar year boundary (autumn risk-premium build-up through
    peak-winter), matching the source's disclosed seasonal pattern. Flat
    otherwise (spring/summer shoulder season).
    """
    df = _prep(price_df)
    close = df["close"]
    doy = close.index.dayofyear

    if window_start_doy <= window_end_doy:
        # Non-wrapping window (not the default case, but supported for
        # generality/grid sweeps).
        in_window = (doy >= window_start_doy) & (doy <= window_end_doy)
    else:
        # Wraps across the year boundary (e.g. Sept -> mid-Feb).
        in_window = (doy >= window_start_doy) | (doy <= window_end_doy)

    position = pd.Series(in_window.astype(int), index=close.index)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
