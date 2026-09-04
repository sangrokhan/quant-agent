"""Strategy: Andean Oscillator bull/bear component crossover with signal-line filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-016):
The Andean Oscillator (alexgrover, 2022, published via Alpaca's blog and
TradingView's open-source library) is an online-algorithm trend
indicator built from exponential envelopes (recursive max/min-with-decay
upper/lower price extremities) applied to both raw and squared close/
open prices, combined into a naive-rolling-variance-style bull and bear
component. Per TradingView's own usage guide: a rising bull component
(green) reflects bullish price variation, a rising bear component (red)
reflects bearish; when bull > bear the market is up-trending. The
source explicitly recommends filtering the raw bull/bear cross with the
indicator's own signal line (EMA of max(bull,bear)) to reduce false
signals: enter when the bull component crosses above the signal line
(source's own stated alternate entry rule).

First Andean Oscillator strategy in this repo -- a 2022-era online
recursive-envelope-variance construction distinct from all prior
Keltner/Bollinger exponential-envelope-based strategies (which measure
fixed-multiplier bands around a moving average, not a naive-variance
spread derived from squared-price envelopes) and from all prior
classic-MA-crossover constructions.

Formula (per Alpaca's blog derivation of alexgrover's original):
  alpha = 2 / (length + 1)
  up_t = max(close_t, open_t, up_{t-1} - (up_{t-1} - close_t) * alpha)
  dn_t = min(close_t, open_t, dn_{t-1} + (close_t - dn_{t-1}) * alpha)
  sq_up_t = max(close_t^2, open_t^2, sq_up_{t-1} - (sq_up_{t-1} - close_t^2) * alpha)
  sq_dn_t = min(close_t^2, open_t^2, sq_dn_{t-1} + (close_t^2 - sq_dn_{t-1}) * alpha)
  bull_t = sqrt(max(sq_dn_t - dn_t^2, 0))
  bear_t = sqrt(max(sq_up_t - up_t^2, 0))
  signal_t = EMA(max(bull_t, bear_t), signal_length)

Signal logic
------------
- Entry (long): bull component crosses above the signal line (source's
  filtered entry rule, reduces false crossover signals vs. the raw
  bull-crosses-bear rule).
- Exit: bear component crosses above the bull component (trend flips
  bearish), or a max_hold_days time-stop backstop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _andean(close: pd.Series, open_: pd.Series, length: int, signal_length: int):
    c = close.to_numpy()
    o = open_.to_numpy()
    n = len(c)
    alpha = 2.0 / (length + 1.0)

    up = np.zeros(n)
    dn = np.zeros(n)
    sq_up = np.zeros(n)
    sq_dn = np.zeros(n)

    up[0] = max(c[0], o[0])
    dn[0] = min(c[0], o[0])
    sq_up[0] = max(c[0] ** 2, o[0] ** 2)
    sq_dn[0] = min(c[0] ** 2, o[0] ** 2)

    for t in range(1, n):
        up[t] = max(c[t], o[t], up[t - 1] - (up[t - 1] - c[t]) * alpha)
        dn[t] = min(c[t], o[t], dn[t - 1] + (c[t] - dn[t - 1]) * alpha)
        sq_up[t] = max(c[t] ** 2, o[t] ** 2, sq_up[t - 1] - (sq_up[t - 1] - c[t] ** 2) * alpha)
        sq_dn[t] = min(c[t] ** 2, o[t] ** 2, sq_dn[t - 1] + (c[t] ** 2 - sq_dn[t - 1]) * alpha)

    bull = np.sqrt(np.clip(sq_dn - dn ** 2, 0.0, None))
    bear = np.sqrt(np.clip(sq_up - up ** 2, 0.0, None))

    bull_s = pd.Series(bull, index=close.index)
    bear_s = pd.Series(bear, index=close.index)
    signal = pd.concat([bull_s, bear_s], axis=1).max(axis=1).ewm(span=signal_length, adjust=False).mean()

    return bull_s, bear_s, signal


def generate_signals(
    price_df: pd.DataFrame,
    length: int = 25,
    signal_length: int = 9,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"] if "open" in df.columns else close.shift(1).fillna(close)

    bull, bear, signal = _andean(close, open_, length, signal_length)

    bull_above_signal = bull > signal
    entry = bull_above_signal & (~bull_above_signal.shift(1).fillna(False))
    exit_signal = bear > bull

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
    daily_ret = position.shift(1).fillna(0) * close.pct_change().fillna(0.0)
    return daily_ret
