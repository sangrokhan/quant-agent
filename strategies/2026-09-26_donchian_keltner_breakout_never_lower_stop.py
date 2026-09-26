"""Strategy: Zarattini/Antonacci Century-of-Industry-Trends breakout+trailing-stop.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-26-011):
Per QuantifiedStrategies.com's summary of Carlo Zarattini & Gary Antonacci's
paper "A Century of Profitable Industry Trends" (https://quantifiedstrategies.substack.com/p/a-trend-following-strategy-18-annually,
free/fully disclosed rule): a simple breakout system entered on either a
Donchian Channel breakout (close > rolling 20-day high) OR a Keltner
Channel breakout (close > 20-day EMA + 1.4x ATR), long-only, exited via a
trailing stop set at the HIGHER of the 40-day-lookback lower Donchian band
and the 40-day-lookback lower Keltner band -- and once set, the stop is
NEVER LOWERED (only ratchets up as price advances), "allowing profits to
run while cutting losing trades quickly". Source's own century-long
backtest (48 industries, cross-sectional + vol-targeted position sizing):
18.2% annualized, Sharpe 1.39 vs market's 0.63, MDD 33% vs 84% for the
market. Adapted here to a SINGLE-SYMBOL long-only implementation (this
repo's loaders/validators operate per-symbol, not cross-sectionally across
48 industries) -- the entry/exit mechanic itself (dual-channel OR-breakout
entry + never-lowered dual-channel trailing stop) is tested exactly as
disclosed; the cross-sectional vol-targeted position-sizing/200%-leverage
overlay from the source's portfolio-level implementation is out of scope
for this repo's single-asset backtest framework.

First strategy in this repo combining Donchian AND Keltner breakouts as an
OR-gated entry with a MAX-of-both-lower-bands trailing stop that never
retreats -- distinct from every existing Donchian-only or Keltner-only
breakout/channel entry (18+ prior Donchian entries, 54+ prior Keltner
entries per KB grep, none combine both channels this way).

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
    entry_window: int = 20,
    stop_window: int = 40,
    keltner_ema_window: int = 20,
    keltner_atr_window: int = 20,
    keltner_mult: float = 1.4,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    donchian_upper = high.rolling(entry_window).max().shift(1)
    donchian_lower_stop = low.rolling(stop_window).min().shift(1)

    keltner_ema = close.ewm(span=keltner_ema_window, adjust=False).mean()
    atr_entry = _atr(high, low, close, keltner_atr_window)
    keltner_upper = (keltner_ema + keltner_mult * atr_entry).shift(1)

    atr_stop = _atr(high, low, close, stop_window)
    keltner_lower_stop = (keltner_ema - keltner_mult * atr_stop).shift(1)

    entry = (close > donchian_upper) | (close > keltner_upper)
    stop_level_raw = pd.concat([donchian_lower_stop, keltner_lower_stop], axis=1).max(axis=1)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    trailing_stop = None
    for i in range(len(close)):
        if in_position:
            candidate_stop = stop_level_raw.iloc[i]
            if pd.notna(candidate_stop):
                trailing_stop = candidate_stop if trailing_stop is None else max(trailing_stop, candidate_stop)
            if trailing_stop is not None and close.iloc[i] < trailing_stop:
                in_position = False
                trailing_stop = None
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                trailing_stop = stop_level_raw.iloc[i] if pd.notna(stop_level_raw.iloc[i]) else None
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
