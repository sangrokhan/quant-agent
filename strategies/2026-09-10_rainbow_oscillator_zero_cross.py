"""Strategy: Rainbow Oscillator (multi-EMA normalized-deviation average) zero-line cross.

Hypothesis (see knowledge_base/strategies_log.jsonl for this run's id):
Per https://alphax.trading/dictionary/rainbow-oscillator (visited this
iteration), the Rainbow Oscillator is distinct from this repo's already-tested
"Rainbow Moving Average" (recursive cascade of SMAs, id 2026-09-04-135 /
2026-09-05-070) and "Zero-Lag Rainbow %B" (Vervoort TASC construction, id
2026-09-06-119): its disclosed formula computes, for a set of N EMA periods,
the PERCENTAGE deviation of price from each EMA, then averages those N
normalized deviation values into one aggregated "Rainbow_Value" oscillator:

    For i = 1..N:
        Line[i] = EMA(Price, Period[i])
        Oscillator[i] = (Price - Line[i]) / Line[i] * 100
    Rainbow_Value = mean(Oscillator[1..N])

The source states divergence/fanning of the underlying EMA lines signals
accelerating momentum, and its own "Execution Rules for Systematic Traders"
gives a shortest-vs-longest EMA crossover as one operationalization -- but
that reduces to an already-heavily-tested plain EMA crossover. This strategy
instead directly operationalizes the source's own headline aggregated
Rainbow_Value construction (not disclosed by the source as a discrete rule,
but the natural zero-crossing analog other multi-line oscillators in this
repo use, e.g. TRIX/PPO/KST zero-line crosses): Rainbow_Value crossing above
zero means price is, on net across the whole period spectrum (short to
long), trading above its EMAs -- a broad multi-timeframe bullish alignment
signal; crossing below zero means net alignment turned bearish. First
Rainbow OSCILLATOR (deviation-average) strategy in this repo -- distinct
construction from the cascade-of-SMAs Rainbow MA and the Vervoort Rainbow
%B already tested.

Signal logic
------------
- Entry (long): Rainbow_Value crosses from <=0 to >0.
- Exit: Rainbow_Value crosses back to <=0, or a max_hold_days time-stop.
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


def _rainbow_value(close: pd.Series, periods: tuple[int, ...]) -> pd.Series:
    oscillators = []
    for p in periods:
        ema = close.ewm(span=p, adjust=False).mean()
        osc = (close - ema) / ema * 100.0
        oscillators.append(osc)
    return pd.concat(oscillators, axis=1).mean(axis=1)


def generate_signals(
    price_df: pd.DataFrame,
    periods: tuple[int, ...] = (5, 10, 20, 50, 100),
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rainbow = _rainbow_value(close, periods)
    warmup = max(periods)

    entry_signal = (rainbow > 0) & (rainbow.shift(1) <= 0)
    exit_signal = rainbow <= 0

    valid = pd.Series(True, index=df.index)
    valid.iloc[:warmup] = False

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = None

    for i in range(len(df.index)):
        if not valid.iloc[i]:
            position.iloc[i] = 0
            continue

        if in_position:
            held_days = i - entry_idx
            if exit_signal.iloc[i] or held_days >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_signal.iloc[i]:
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    periods: tuple[int, ...] = (5, 10, 20, 50, 100),
    max_hold_days: int = 30,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(price_df, periods=periods, max_hold_days=max_hold_days)

    daily_ret = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(int) * daily_ret
    strat_returns.name = "strategy_returns"
    return strat_returns
