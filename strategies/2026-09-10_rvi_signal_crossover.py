"""Strategy: Relative Vigor Index (RVI) signal-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl for this run's id):
Per Investopedia's Relative Vigor Index guide
(https://www.investopedia.com/terms/r/relative_vigor_index.asp): the RVI is
a momentum oscillator comparing a security's close-vs-open (numerator) to
its high-vs-low trading range (denominator), each 4-bar-weighted-averaged
(weights 1,2,2,1) then SMA-smoothed over N periods -- calculated similarly
to the Stochastic Oscillator but using close-vs-OPEN rather than
close-vs-LOW. Source's own disclosed rule: an RVI crossover above its own
signal line (a further 4-bar weighted average of RVI itself) is bullish;
below is bearish. First RVI strategy in this repo -- distinct from every
other oscillator already tested (Stochastic uses close-vs-low, RSI uses
gain/loss ratio, this uses close-vs-open).

Calculation (per Investopedia's exact formula):
    a[t] = close[t] - open[t]
    numerator[t] = SMA_N( (a + 2*a.shift(1) + 2*a.shift(2) + a.shift(3)) / 6 )
    e[t] = high[t] - low[t]
    denominator[t] = SMA_N( (e + 2*e.shift(1) + 2*e.shift(2) + e.shift(3)) / 6 )
    RVI[t] = numerator[t] / denominator[t]
    signal_line[t] = (RVI + 2*RVI.shift(1) + 2*RVI.shift(2) + RVI.shift(3)) / 6

Signal logic
------------
- Entry (long): RVI crosses above signal_line (bullish crossover).
- Exit: RVI crosses below signal_line, or a max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _weighted4(series: pd.Series) -> pd.Series:
    """4-bar weighted average with weights 1,2,2,1 (current, -1, -2, -3)."""
    return (
        series
        + 2 * series.shift(1)
        + 2 * series.shift(2)
        + series.shift(3)
    ) / 6.0


def _rvi(df: pd.DataFrame, n_period: int) -> tuple[pd.Series, pd.Series]:
    close = df["close"]
    open_ = df["open"]
    high = df["high"]
    low = df["low"]

    a = close - open_
    e = high - low

    numerator = _weighted4(a).rolling(n_period).mean()
    denominator = _weighted4(e).rolling(n_period).mean()

    rvi = numerator / denominator.replace(0, pd.NA)
    signal_line = _weighted4(rvi)
    return rvi, signal_line


def generate_signals(
    price_df: pd.DataFrame,
    n_period: int = 10,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)

    rvi, signal_line = _rvi(df, n_period)

    bullish_cross = (rvi > signal_line) & (rvi.shift(1) <= signal_line.shift(1))
    bearish_cross = (rvi < signal_line) & (rvi.shift(1) >= signal_line.shift(1))

    valid = rvi.notna() & signal_line.notna()

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = None

    for i in range(len(df.index)):
        if not valid.iloc[i]:
            position.iloc[i] = 0
            continue

        if in_position:
            held_days = i - entry_idx
            if bearish_cross.iloc[i] or held_days >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bullish_cross.iloc[i]:
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    n_period: int = 10,
    max_hold_days: int = 20,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(price_df, n_period=n_period, max_hold_days=max_hold_days)

    daily_ret = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(int) * daily_ret
    strat_returns.name = "strategy_returns"
    return strat_returns
