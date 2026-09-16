"""Strategy: True Strength Index (TSI, William Blau) centerline crossover
with a signal-line confirmation filter.

Hypothesis (grounded in Step 2 research this iteration):
Per StockCharts ChartSchool
(https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/true-strength-index,
visited this iteration): TSI = 100 * doubly-smoothed price change /
doubly-smoothed absolute price change, where "doubly-smoothed" means an
EMA(long_period) of the raw daily price change, then an EMA(short_period) of
that result (default long_period=25, short_period=13 per Blau's original).
The source's own disclosed rules: "the bulls have the momentum edge when TSI
is positive and the bears have the edge when it's negative" (centerline
crossover, "the purest signal") and "as with MACD, a signal line can be
applied to identify upturns and downturns... signal line crossovers are
however quite frequent and require further filtering with other
techniques". This strategy implements exactly that combination: long only
when TSI is above zero AND TSI is above its own EMA(signal_period) signal
line (the source's own suggested extra filter on top of the "purest"
centerline signal), flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _tsi(close: pd.Series, long_period: int, short_period: int) -> pd.Series:
    price_change = close.diff()
    abs_change = price_change.abs()

    smoothed_change = price_change.ewm(span=long_period, adjust=False).mean()
    double_smoothed_change = smoothed_change.ewm(span=short_period, adjust=False).mean()

    smoothed_abs = abs_change.ewm(span=long_period, adjust=False).mean()
    double_smoothed_abs = smoothed_abs.ewm(span=short_period, adjust=False).mean()

    tsi = 100 * double_smoothed_change / double_smoothed_abs.replace(0.0, pd.NA)
    return tsi.astype(float)


def generate_signals(
    price_df: pd.DataFrame,
    long_period: int = 25,
    short_period: int = 13,
    signal_period: int = 7,
) -> pd.Series:
    """Return a 0/1 position series.

    Long when TSI > 0 (bullish centerline regime, source's "purest signal")
    AND TSI > its own EMA(signal_period) signal line (source's disclosed
    extra filter on top of the centerline crossover).
    """
    df = _prep(price_df)
    close = df["close"]

    tsi = _tsi(close, long_period, short_period)
    signal_line = tsi.ewm(span=signal_period, adjust=False).mean()

    position = ((tsi > 0) & (tsi > signal_line)).astype(float)
    position = position.fillna(0.0)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    long_period: int = 25,
    short_period: int = 13,
    signal_period: int = 7,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        long_period=long_period,
        short_period=short_period,
        signal_period=signal_period,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret
