"""Strategy: Schaff Trend Cycle (STC) centerline (50) crossover, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-080):
The Schaff Trend Cycle (Doug Schaff) is a modified MACD that applies a
double stochastic %K/%D smoothing cycle on top of the raw MACD line to
filter market noise and identify short-term trend cycles faster than a
plain MACD. It oscillates 0-100: above 50 signals an uptrend, below 50 a
downtrend. Per EnlightenedStockTrading's worked systematic-trading example:
"a trader may create a trading algorithm that enters long positions when
the STC line crosses above 50 and exits when it crosses below 50."
Corroborated by a PineScriptForge search snippet using a 25/75
oversold/overbought variant instead -- the 50-centerline version is used
here as the more explicitly-worked example. Distinct from MACD (already
tested at 2026-09-03-013, raw EMA-difference with a zero-line filter, no
cyclical smoothing) and from Stochastic/StochRSI (apply the stochastic
formula to price/RSI, not to a MACD-derived series).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _stoch_of_series(series: pd.Series, cycle: int) -> pd.Series:
    lo = series.rolling(cycle).min()
    hi = series.rolling(cycle).max()
    rng = (hi - lo).replace(0, pd.NA)
    return 100.0 * (series - lo) / rng


def _stc(close: pd.Series, fast: int, slow: int, cycle: int, factor: float) -> pd.Series:
    macd = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()

    # First smoothing pass: stochastic of MACD, then recursive %D smoothing.
    k1 = _stoch_of_series(macd, cycle).fillna(0.0)
    d1 = pd.Series(index=close.index, dtype=float)
    prev = 0.0
    for i in range(len(d1)):
        prev = prev + factor * (k1.iloc[i] - prev)
        d1.iloc[i] = prev

    # Second smoothing pass: stochastic of the first %D, then recursive %D again.
    k2 = _stoch_of_series(d1, cycle).fillna(0.0)
    stc = pd.Series(index=close.index, dtype=float)
    prev = 0.0
    for i in range(len(stc)):
        prev = prev + factor * (k2.iloc[i] - prev)
        stc.iloc[i] = prev

    return stc


def generate_signals(
    price_df: pd.DataFrame,
    fast: int = 23,
    slow: int = 50,
    cycle: int = 10,
    factor: float = 0.5,
    centerline: float = 50.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry: STC crosses above ``centerline`` (default 50).
    Exit: STC crosses back below ``centerline``.
    """
    df = _prep(price_df)
    close = df["close"]
    stc = _stc(close, fast, slow, cycle, factor)

    cross_up = (stc > centerline) & (stc.shift(1) <= centerline)
    cross_down = (stc < centerline) & (stc.shift(1) >= centerline)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    for i in range(len(df)):
        if in_position:
            if bool(cross_down.iloc[i]) if not pd.isna(cross_down.iloc[i]) else False:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]) if not pd.isna(cross_up.iloc[i]) else False:
                in_position = True
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
