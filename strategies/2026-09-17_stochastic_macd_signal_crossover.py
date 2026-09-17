"""Strategy: Apirine Stochastic MACD Oscillator (STMACD) signal-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-155):
Vitali Apirine's Traders' Tips article (TASC Nov 2019, "The Stochastic MACD
Oscillator", source: Traders.com Nov 2019 Traders' Tips, TradeStation
EasyLanguage code read this iteration) combines the classic stochastic
oscillator's normalization (against the rolling high/low range) with the
MACD's fast/slow EMA spread, producing a bounded-ish oscillator whose
crossovers of its own EMA signal line and fixed +-10 overbought/oversold
bands should mark momentum-shift entries -- similar spirit to classic MACD
signal-line crossover strategies already in this repo but with the
stochastic normalization changing the oscillator's amplitude/timing profile
(range-normalized rather than raw price-difference). First
stochastic-normalized-MACD strategy in this repo.

Formula (per source)
---------------------
- HHigh = rolling max(High, periods), LLow = rolling min(Low, periods).
- FastAvg = EMA(Close, fast_length), SlowAvg = EMA(Close, slow_length).
- FastStoch = (FastAvg - LLow) / (HHigh - LLow)
- SlowStoch = (SlowAvg - LLow) / (HHigh - LLow)
- STMACD = (FastStoch - SlowStoch) * 100
- STMACD signal = EMA(STMACD, signal_length)

Signal logic (long-only adaptation)
------------------------------------
- Entry (long): STMACD crosses above its signal line while STMACD is below
  `overbought` (avoid buying an already-extended move) -- OR STMACD crosses
  up from below `oversold` (a distinct, more conservative "oversold bounce"
  entry mode is not separately implemented; kept to one clean rule set for
  simplicity): here we use the plain bullish signal-line crossover as the
  entry trigger, matching the original TradeStation-style momentum-oscillator
  usage.
- Exit: STMACD crosses below its signal line, OR after `max_hold_days`.
- No short leg (repo convention: long/flat only).

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


def _stochastic_macd(df: pd.DataFrame, periods: int, fast_len: int, slow_len: int, signal_len: int):
    high = df["high"]
    low = df["low"]
    close = df["close"]

    hhigh = high.rolling(periods).max()
    llow = low.rolling(periods).min()
    rng = (hhigh - llow).replace(0, pd.NA)

    fast_avg = close.ewm(span=fast_len, adjust=False).mean()
    slow_avg = close.ewm(span=slow_len, adjust=False).mean()

    fast_stoch = (fast_avg - llow) / rng
    slow_stoch = (slow_avg - llow) / rng

    stmacd = (fast_stoch - slow_stoch) * 100
    stmacd = stmacd.astype(float)
    signal = stmacd.ewm(span=signal_len, adjust=False).mean()
    return stmacd, signal


def generate_signals(
    price_df: pd.DataFrame,
    periods: int = 45,
    fast_len: int = 12,
    slow_len: int = 26,
    signal_len: int = 9,
    overbought: float = 10.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    stmacd, signal = _stochastic_macd(df, periods, fast_len, slow_len, signal_len)

    bullish_cross = (stmacd.shift(1) <= signal.shift(1)) & (stmacd > signal) & (stmacd < overbought)
    bearish_cross = (stmacd.shift(1) >= signal.shift(1)) & (stmacd < signal)

    close = df["close"]
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if i < periods:
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
