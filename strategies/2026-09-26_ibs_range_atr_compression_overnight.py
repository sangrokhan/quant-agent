"""Strategy: Volatility Compression Overnight (IBS + Range/ATR ratio).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-26-018):
Per QuantifiedStrategies.com's "A Volatility Compression Trading Strategy
(Only 4% Drawdown)" (https://www.quantifiedstrategies.com/a-volatility-compression-trading-strategy/,
disclosed via Google AI-overview synthesis of the free article -- two
simple, fully disclosed rules): (1) IBS (Internal Bar Strength =
(Close-Low)/(High-Low)) must be <= 0.10 (close near the day's own low);
(2) the day's own range (High-Low) must be LESS than range_atr_ratio
(source: 60%) of the 14-day ATR (an unusually tight, compressed trading
range for that instrument's recent volatility). When BOTH conditions are
true simultaneously, buy at the close; exit next day at either the open
or the close (source's own overnight-to-next-day single-bar hold,
occasionally carried over a weekend on Fridays). This implementation uses
the next-day CLOSE exit variant (the `exit_at_open` param toggles to the
open-exit variant for a future iteration's parameter sweep).

First strategy in this repo combining IBS (near-day-low close) with a
RANGE-COMPRESSED-RELATIVE-TO-ATR filter (day's own range unusually narrow
vs its own volatility) as a joint entry gate -- distinct from every other
IBS-family entry (which pair IBS with RSI/SMA/streak-count filters, not an
ATR-relative range-compression condition) and from every ATR-percentile
strategy (which filter on the ATR itself, not the ratio of a single bar's
raw range to its own ATR).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    ibs_threshold: float = 0.10,
    range_atr_ratio: float = 0.60,
    atr_window: int = 14,
    max_hold_days: int = 3,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry: IBS<=ibs_threshold AND (High-Low) < range_atr_ratio * ATR(14)
    at the close. Exit: next bar's close (single-bar overnight hold, per
    source's own "sell at tomorrow's open or close" rule -- using the
    close-exit variant here), with a max_hold_days safety backstop in case
    the exit condition logic needs to carry over a non-trading day.
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    rng = (high - low).replace(0.0, 1e-12)
    ibs = (close - low) / rng

    atr = _atr(high, low, close, atr_window)
    compressed_range = (high - low) < (range_atr_ratio * atr)

    entry = (ibs <= ibs_threshold) & compressed_range

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            # Single-bar overnight hold: exit at the very next bar's close.
            if held >= 1 or held >= max_hold_days:
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
