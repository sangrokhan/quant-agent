"""Strategy: Pretty Good Oscillator (PGO, Mark Johnson) breakout-momentum
crossover, long-only.

Hypothesis (grounded in Step 2 research this iteration):
Per https://www.quantifiedstrategies.com/pretty-good-oscillator/ (visited
this iteration): PGO = (close - SMA(n)) / EMA(true_range, n), a momentum
oscillator expressing how many average-true-ranges the current close sits
above/below its own SMA. Source's own disclosed thresholds: "values above
+2 could indicate an overbought market" and "in a strongly trending market,
the indicator rising above +2 ... suggests increasing momentum, which could
help confirm a breakout" (i.e. +2 is read as bullish breakout confirmation,
not a mean-reversion sell signal, since "this is a trend-following
strategy"); values below 0 mark the loss of bullish momentum. Implemented
long-only: enter when PGO crosses up through +breakout_level (source's own
disclosed breakout-confirmation threshold), exit when PGO crosses back down
through exit_level (source's own zero-line "bearish momentum" threshold),
held via this asymmetric entry/exit band (a wide trend-following filter
rather than a tight mean-reversion oscillator read).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _pgo(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    sma = close.rolling(period, min_periods=period // 2).mean()
    tr = _true_range(high, low, close)
    atr_ema = tr.ewm(span=period, adjust=False).mean()
    pgo = (close - sma) / atr_ema.replace(0.0, np.nan)
    return pgo.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 14,
    breakout_level: float = 2.0,
    exit_level: float = 0.0,
) -> pd.Series:
    """Return a 0/1 position series.

    Long-only: enter when PGO crosses up through `breakout_level` (source's
    own trend-following breakout-confirmation threshold), exit when PGO
    crosses down through `exit_level`, held via hysteresis in between.
    """
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    pgo = _pgo(high, low, close, period)
    pgo_arr = pgo.to_numpy()

    position = np.zeros(len(close), dtype=float)
    held = 0.0
    prev = 0.0
    for i, val in enumerate(pgo_arr):
        if held == 0.0:
            if prev < breakout_level <= val:
                held = 1.0
        else:
            if prev > exit_level >= val:
                held = 0.0
        position[i] = held
        prev = val

    return pd.Series(position, index=close.index)


def generate_returns(
    price_df: pd.DataFrame,
    period: int = 14,
    breakout_level: float = 2.0,
    exit_level: float = 0.0,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        period=period,
        breakout_level=breakout_level,
        exit_level=exit_level,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret
