"""Strategy: Price Volume Trend (PVT) signal-line crossover, trend-filtered.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-095):
Per Google AI-overview synthesis (Switch Stats/Phemex/StockGro/query
"Price Volume Trend PVT indicator strategy exact entry exit rules"): PVT
(Price Volume Trend, a cumulative volume indicator that scales each bar's
volume by the day's percentage price change rather than On-Balance
Volume's simple +/-full-volume step, filtering out minor noise and
highlighting real institutional accumulation) crossing above its own
21-period signal-line SMA while price is above a longer-term trend SMA
signals a long entry (bullish macro environment + PVT-confirmed
accumulation). Exit when PVT crosses back below its own signal line.

First Price Volume Trend strategy in this repo (0 prior hits on "Price
Volume Trend"/"PVT" in strategies_index.jsonl) -- distinct from OBV
(step function of full daily volume, not price-change-scaled) and from
Klinger/Chaikin/Force Index (different volume-weighting constructions).

Signal logic
------------
- PVT[0] = 0; PVT[t] = PVT[t-1] + volume[t] * (close[t] - close[t-1]) / close[t-1]
- signal_line = SMA(PVT, signal_window) [source default: 21]
- trend_sma = SMA(close, trend_window) [source default: 50 or 200]
- Entry (long): close > trend_sma (bullish macro trend filter) AND PVT
  crosses from at/below its signal line to above it (bullish crossover)
  AND today's close > yesterday's close (source's "confirmation: candle
  closes green" rule).
- Exit: PVT crosses back below its signal line (source's primary exit
  rule), OR close falls below (entry_price - atr_mult*ATR) as a hard
  stop-loss approximating the source's "beneath the immediate local
  swing low" rule, OR a max_hold_days time-stop backstop (source has no
  explicit time-stop, added here as a standard backstop against
  indefinite holds).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def _compute_pvt(close: pd.Series, volume: pd.Series) -> pd.Series:
    pct_change = close.pct_change().fillna(0.0)
    daily_contrib = volume * pct_change
    return daily_contrib.cumsum()


def generate_signals(
    price_df: pd.DataFrame,
    signal_window: int = 21,
    trend_window: int = 50,
    atr_window: int = 14,
    atr_mult: float = 2.5,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    pvt = _compute_pvt(close, volume)
    signal_line = pvt.rolling(signal_window).mean()
    trend_sma = close.rolling(trend_window).mean()
    atr = _atr(df, atr_window)

    above_signal = pvt > signal_line
    bullish_cross = above_signal & (~above_signal.shift(1).fillna(False))
    green_candle = close > close.shift(1)
    trend_ok = close > trend_sma

    entry = bullish_cross & green_candle & trend_ok.fillna(False)
    exit_cross = ~above_signal

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_price = None

    for i in range(n):
        if in_position:
            held = i - entry_idx
            atr_val = atr.iloc[i]
            stop_hit = False
            if entry_price is not None and atr_val == atr_val and atr_val is not None:
                stop_hit = close.iloc[i] < (entry_price - atr_mult * atr_val)
            if bool(exit_cross.iloc[i]) or stop_hit or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                entry_price = None
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                entry_price = close.iloc[i]
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
