"""Strategy: Sentiment Zone Oscillator (SZO, Walid Khalil MFTA/CFTe) contrarian
oversold-bounce mean-reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-118):
Per TASC May 2012 Traders' Tips excerpt by Walid Khalil (creator of the
already-tested VZO/Volume Zone Oscillator and PZO/Price Zone Oscillator):
the Sentiment Zone Oscillator (SZO) measures extreme bullish/bearish
sentiment via a simple up-day/down-day count, smoothed with a TEMA:

    daily_sign = +1 if close > prior close, else -1
    SP (sentiment position) = X-day TEMA(daily_sign)
    SZO = 100 * (SP / X)

Author's own disclosed thresholds: SZO > +7 = extreme optimism
(overbought), SZO < -7 = extreme pessimism (oversold). The author's
sample chart (DJIA, Jul 2007-Apr 2008) showed contrarian reversal signals
at these extremes ("all four signals successful"). First Sentiment Zone
Oscillator strategy in this repo (0 prior matches) -- distinct construction
from VZO (volume-based) and PZO (price/typical-price-based), since SZO
uses pure up/down-day COUNT with no volume or price-magnitude weighting.

Signal logic (long-only contrarian mean reversion)
---------------------------------------------------
- Entry (long): SZO crosses below the oversold_threshold (default -7,
  extreme pessimism -> contrarian buy).
- Exit: SZO crosses back above the exit_threshold (default 0.0, sentiment
  neutralizing) OR a max_hold_days safety time-stop.
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


def _tema(series: pd.Series, window: int) -> pd.Series:
    ema1 = series.ewm(span=window, adjust=False).mean()
    ema2 = ema1.ewm(span=window, adjust=False).mean()
    ema3 = ema2.ewm(span=window, adjust=False).mean()
    return 3 * (ema1 - ema2) + ema3


def _szo(close: pd.Series, window: int) -> pd.Series:
    daily_sign = (close.diff() > 0).astype(float) * 2 - 1  # +1 up, -1 down/flat
    sp = _tema(daily_sign, window)
    szo = 100.0 * (sp / window)
    return szo


def generate_signals(
    price_df: pd.DataFrame,
    szo_window: int = 14,
    oversold_threshold: float = -7.0,
    exit_threshold: float = 0.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    szo = _szo(close, szo_window)

    entry = (szo.shift(1) >= oversold_threshold) & (szo < oversold_threshold)
    exit_signal = (szo.shift(1) <= exit_threshold) & (szo > exit_threshold)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
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
