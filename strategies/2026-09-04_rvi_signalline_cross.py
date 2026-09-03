"""Strategy: Relative Vigor Index (RVI) signal-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-061):
Per QuantifiedStrategies' RVI article: the Relative Vigor Index measures
price momentum by comparing close-to-open movement to the high-low
trading range, smoothed with a 4-bar triangular (1:2:2:1) weighting
kernel -- distinct from every prior oscillator in this repo. Source's
general rule: RVI crossing above its own signal line (a further 4-bar
weighted smoothing of RVI itself) signals a bullish momentum shift.
Source's own paywalled backtest reports the strategy works on gold/crypto
but explicitly NOT on SPY/TLT -- crypto is tested here as a genuine
confirmation opportunity of that specific claim.

RVI formula (standard):
    a_t = close_t - open_t
    numerator_t = (a_t + 2*a_{t-1} + 2*a_{t-2} + a_{t-3}) / 6
    range_t = high_t - low_t
    denominator_t = (range_t + 2*range_{t-1} + 2*range_{t-2} + range_{t-3}) / 6
    RVI_t = SMA(numerator, n) / SMA(denominator, n)
    signal_t = (RVI_t + 2*RVI_{t-1} + 2*RVI_{t-2} + RVI_{t-3}) / 6

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


def _weighted4(x: pd.Series) -> pd.Series:
    """4-bar triangular (1:2:2:1) weighted average, current + 3 lags."""
    return (x + 2 * x.shift(1) + 2 * x.shift(2) + x.shift(3)) / 6.0


def _rvi(df: pd.DataFrame, window: int = 10) -> tuple[pd.Series, pd.Series]:
    a = df["close"] - df["open"]
    rng = df["high"] - df["low"]

    numerator = _weighted4(a)
    denominator = _weighted4(rng)

    num_sma = numerator.rolling(window).mean()
    den_sma = denominator.rolling(window).mean()
    rvi = num_sma / den_sma.replace(0, pd.NA)

    signal = _weighted4(rvi)
    return rvi, signal


def generate_signals(
    price_df: pd.DataFrame,
    rvi_window: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rvi, signal = _rvi(df, window=rvi_window)

    entry_signal = (rvi > signal) & (rvi.shift(1) <= signal.shift(1))
    exit_signal = (rvi < signal) & (rvi.shift(1) >= signal.shift(1))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
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
