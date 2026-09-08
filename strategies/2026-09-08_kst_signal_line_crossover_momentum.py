"""Strategy: Pring's Know Sure Thing (KST) signal-line crossover, momentum.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per Investopedia's "Understanding the Know Sure Thing (KST) Oscillator"
(https://www.investopedia.com/terms/k/know-sure-thing-kst.asp), the KST is a
weighted sum of four smoothed rate-of-change (ROC) terms of increasing
lookback, each individually SMA-smoothed (RCMA), designed by Martin Pring
to capture short/intermediate/long-cycle momentum in one composite line:

    RCMA1 = SMA(ROC(close, roc1), sma1)
    RCMA2 = SMA(ROC(close, roc2), sma2)
    RCMA3 = SMA(ROC(close, roc3), sma3)
    RCMA4 = SMA(ROC(close, roc4), sma4)
    KST   = 1*RCMA1 + 2*RCMA2 + 3*RCMA3 + 4*RCMA4
    Signal = SMA(KST, signal_window)

Source's own trading rule: "Trading signals are generated when the KST
crosses over the signal line" (bullish cross = go long / buy momentum
turning up; bearish cross = exit). We implement the long-only version of
this signal-line crossover as a momentum-following entry, distinct from
every prior indicator family in this repo (first Know Sure Thing / Pring
composite-ROC-momentum entry; grep of strategies_index.jsonl for "KST"/
"Know Sure Thing" returns zero matches). Distinct from single-period ROC/
Momentum-oscillator entries already tested since KST's edge (per Pring) is
specifically the multi-timeframe weighted composite, not a single ROC.

A max_hold_days time-stop backstop is added (common pattern in this repo)
since the source's pure crossover-only exit can hold indefinitely through
a slow bearish drift before the signal line finally crosses back down.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
        Position-weighted daily strategy returns (no transaction costs).
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        {0, 1} long/flat position series aligned to price_df.index.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _roc(close: pd.Series, period: int) -> pd.Series:
    return (close / close.shift(period) - 1.0) * 100.0


def _kst(
    close: pd.Series,
    roc1: int,
    roc2: int,
    roc3: int,
    roc4: int,
    sma1: int,
    sma2: int,
    sma3: int,
    sma4: int,
) -> pd.Series:
    rcma1 = _roc(close, roc1).rolling(sma1).mean()
    rcma2 = _roc(close, roc2).rolling(sma2).mean()
    rcma3 = _roc(close, roc3).rolling(sma3).mean()
    rcma4 = _roc(close, roc4).rolling(sma4).mean()
    return 1 * rcma1 + 2 * rcma2 + 3 * rcma3 + 4 * rcma4


def generate_signals(
    price_df: pd.DataFrame,
    roc1: int = 10,
    roc2: int = 15,
    roc3: int = 20,
    roc4: int = 30,
    sma1: int = 10,
    sma2: int = 10,
    sma3: int = 10,
    sma4: int = 15,
    signal_window: int = 9,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    kst = _kst(close, roc1, roc2, roc3, roc4, sma1, sma2, sma3, sma4)
    signal = kst.rolling(signal_window).mean()

    bullish_cross = (kst > signal) & (kst.shift(1) <= signal.shift(1))
    bearish_cross = (kst < signal) & (kst.shift(1) >= signal.shift(1))

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    valid_start = kst.first_valid_index()
    for i in range(len(close)):
        if valid_start is not None and close.index[i] < valid_start:
            position.iloc[i] = 0
            continue
        if in_position:
            held = i - entry_idx
            if bool(bearish_cross.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(bullish_cross.iloc[i]):
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
