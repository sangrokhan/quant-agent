"""Strategy: Ehlers Z3 double-differenced momentum ROC crossover (TASC Jun 2021 baseline).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-161):
John Ehlers' Traders' Tips article "Creating More Robust Trading Strategies
With The FM Demodulator" (TASC Jun 2021, source: easylanguagemastery.com's
replication of the article's baseline strategy, read this iteration) uses a
"baseline" momentum strategy (before applying the article's FM-demodulator
filter) that computes a double-differenced/zero-integrated momentum measure:
Deriv = Close - Close[2] (2-bar rate of change), then Z3 = sum of the last
4 Deriv values -- per Ehlers' own note, this construction places zeros at
the Nyquist and 2*Nyquist frequencies, effectively integrating the raw
derivative while suppressing high-frequency noise components. Z3 is then
smoothed (Signal = SMA(Z3, sig_period)) and its own rate of change (ROC =
Signal - Signal[roc_period]) crossing zero triggers entries. This specific
Z3 construction (sum of 4 consecutive 2-bar derivatives) is a novel
momentum-smoothing mechanic in this repo, distinct from standard
ROC/MACD/TRIX momentum measures.

Formula (per source)
---------------------
- Deriv(t) = Close(t) - Close(t-2)
- Z3(t) = Deriv(t) + Deriv(t-1) + Deriv(t-2) + Deriv(t-3)
- Signal(t) = SMA(Z3, sig_period)
- ROC(t) = Signal(t) - Signal(t - roc_period)

Signal logic (long-only adaptation of the source's stop-and-reverse baseline)
------------------------------------------------------------------------
- Entry (long): ROC crosses above 0.
- Exit: Signal crosses below 0, OR after `max_hold_days`.
- No short leg.

Interface contract for validators (see validation/validators.py):
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


def generate_signals(
    price_df: pd.DataFrame,
    sig_period: int = 8,
    roc_period: int = 1,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    deriv = close - close.shift(2)
    z3 = deriv + deriv.shift(1) + deriv.shift(2) + deriv.shift(3)
    signal = z3.rolling(sig_period).mean()
    roc = signal - signal.shift(roc_period)

    entry = (roc.shift(1) <= 0) & (roc > 0)
    exit_signal = (signal.shift(1) >= 0) & (signal < 0)

    warmup = sig_period + roc_period + 4

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if i < warmup:
            position.iloc[i] = 0
            continue
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
