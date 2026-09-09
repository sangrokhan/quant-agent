"""Strategy: True Strength Index (TSI) signal-line crossover, gated by a
200-day SMA uptrend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl for this run's id):
Per Quantified Strategies' TSI explainer
(https://quantifiedstrategies.substack.com/p/true-strength-index-tsi-trading-strategy):
the True Strength Index (William Blau) is a double-smoothed momentum
oscillator, TSI = 100 * doubleEMA(price_change, long, short) /
doubleEMA(abs(price_change), long, short) (classic settings 25/13), with an
EMA signal line. A bullish signal-line crossover (TSI crosses above its own
EMA signal line) indicates strengthening upside momentum -- conceptually
similar to a MACD signal-line cross but built from double-smoothed price
change rather than a difference of two EMAs. This repo has no prior TSI
strategy (0 hits in strategies_index.jsonl). To avoid the well-documented
whipsaw problem of trading raw oscillator crossovers in choppy/downtrending
markets (a pattern this repo has repeatedly found improves entries, e.g.
2026-09-03-021's SMA200 uptrend gate), this version only takes the crossover
long when price is also above its 200-day SMA (uptrend confirmation).

Signal logic
------------
- price_change = close.diff()
- TSI = 100 * EMA(EMA(price_change, long), short) /
         EMA(EMA(|price_change|, long), short)
- signal_line = EMA(TSI, signal_window)
- Entry (long): TSI crosses above signal_line AND close > SMA(sma_window)
  (uptrend gate).
- Exit: TSI crosses below signal_line, OR the uptrend gate breaks
  (close falls below SMA(sma_window)), OR a max_hold_days time-stop.
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


def _tsi(close: pd.Series, long_window: int, short_window: int) -> pd.Series:
    price_change = close.diff()
    double_smoothed_pc = price_change.ewm(span=long_window, adjust=False).mean()
    double_smoothed_pc = double_smoothed_pc.ewm(span=short_window, adjust=False).mean()

    double_smoothed_apc = price_change.abs().ewm(span=long_window, adjust=False).mean()
    double_smoothed_apc = double_smoothed_apc.ewm(span=short_window, adjust=False).mean()

    tsi = 100 * double_smoothed_pc / double_smoothed_apc.replace(0, pd.NA)
    return tsi


def generate_signals(
    price_df: pd.DataFrame,
    long_window: int = 25,
    short_window: int = 13,
    signal_window: int = 7,
    sma_window: int = 200,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    tsi = _tsi(close, long_window, short_window)
    signal_line = tsi.ewm(span=signal_window, adjust=False).mean()
    sma = close.rolling(sma_window).mean()
    uptrend = close > sma

    bullish_cross = (tsi > signal_line) & (tsi.shift(1) <= signal_line.shift(1))
    bearish_cross = (tsi < signal_line) & (tsi.shift(1) >= signal_line.shift(1))

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = None

    idx_list = df.index
    tsi_valid = tsi.notna() & signal_line.notna() & sma.notna()

    for i, ts in enumerate(idx_list):
        if not tsi_valid.iloc[i]:
            position.iloc[i] = 0
            continue

        if in_position:
            held_days = i - entry_idx
            if bearish_cross.iloc[i] or (not uptrend.iloc[i]) or held_days >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bullish_cross.iloc[i] and uptrend.iloc[i]:
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    long_window: int = 25,
    short_window: int = 13,
    signal_window: int = 7,
    sma_window: int = 200,
    max_hold_days: int = 30,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        long_window=long_window,
        short_window=short_window,
        signal_window=signal_window,
        sma_window=sma_window,
        max_hold_days=max_hold_days,
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(int) * daily_ret
    strat_returns.name = "strategy_returns"
    return strat_returns
