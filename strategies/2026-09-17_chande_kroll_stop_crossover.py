"""Strategy: Chande Kroll Stop dual-line crossover (Tushar Chande / Stanley Kroll).

Source: Google AI-overview synthesis of TradingView/TrendSpider/IBKR Glossary
documentation (browser_exec fallback this iteration -- web_search DDGS/Yahoo
backend failed with RequestError/TLS errors on every query attempted this
iteration), corroborated by IBKR Glossary's own stated rule set:
"Sell when the price crosses below both lines. Buy when the price crosses
above both lines. Trade when the two lines cross each other."

Indicator formula (P = ATR/stop period, X = ATR multiplier, Q = final
lookback period; defaults P=10, X=1, Q=9 per the TradingView/AI-overview
default parameterization):

    initial_high_stop = HighestHigh(P) - X * ATR(P)
    initial_low_stop  = LowestLow(P)  + X * ATR(P)
    short_stop (red line) = HighestValue(initial_high_stop, Q)   # trailing-down resistance
    long_stop  (green line) = LowestValue(initial_low_stop, Q)   # trailing-up support

First Chande Kroll Stop strategy in this repo (0 prior KB hits for "Chande
Kroll"). Distinct from this repo's many ATR-trailing-stop / Chandelier Exit
/ SuperTrend variants because both stop lines here are themselves rolling
extrema of an ATR-buffered high/low over TWO separate lookback windows (P
then Q), not a single ATR band off a moving average or off the extreme
price directly.

Trading rule (source's own IBKR-glossary stated rule, operationalized for
this repo's long-only contract): long entry when close crosses above BOTH
stop lines (i.e. above the long_stop AND above the short_stop -- the
stronger of IBKR's "buy when price crosses above both lines" condition);
exit (flat) when close crosses back below either line, with a
`min_hold_days` hysteresis to reduce whipsaw (this repo's standard
treatment), plus an SMA `trend_window` regime filter and a `max_hold_days`
time-stop for consistency with sibling strategies in this repo.

Interface contract (see validation/grid_test.py, validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def _chande_kroll(df: pd.DataFrame, p: int, x: float, q: int) -> tuple[pd.Series, pd.Series]:
    atr = _atr(df, p)
    highest_high = df["high"].rolling(p).max()
    lowest_low = df["low"].rolling(p).min()

    initial_high_stop = highest_high - x * atr
    initial_low_stop = lowest_low + x * atr

    short_stop = initial_high_stop.rolling(q).max()
    long_stop = initial_low_stop.rolling(q).min()
    return short_stop, long_stop


def generate_signals(
    price_df: pd.DataFrame,
    p: int = 10,
    x: float = 1.0,
    q: int = 9,
    trend_window: int = 100,
    min_hold_days: int = 5,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    short_stop, long_stop = _chande_kroll(df, p, x, q)
    trend_sma = close.rolling(trend_window).mean()

    raw_long_signal = (close > short_stop) & (close > long_stop) & (close > trend_sma)
    raw_exit_signal = (close < short_stop) | (close < long_stop)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            want_flat = bool(raw_exit_signal.iloc[i]) and held >= min_hold_days
            if want_flat or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(raw_long_signal.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
