"""Strategy: RSI(14) oversold-exit with fixed ATR-based 1:2 risk/reward bracket.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-006):
Per FxBacktest.app's original research
(https://fxbacktest.app/research/indicator-signal-win-rates/, 232,772
signals across 28 instruments/16yrs, benchmarked against a MATCHED RANDOM
CONTROL of same direction/stop distance), "RSI(14) exits oversold" (RSI
crossing back above 30 from below) was the single most statistically
significant daily-chart signal at a 1:2 risk/reward target: 34.8% win rate
vs 31.1% for the matched random control (edge +3.7pts, marked significant
at p<0.05-ish "*"). Their method: enter at next-bar open, stop = 1.5*ATR(14),
target = 2x that distance (1:2 R:R), walk trades forward up to 40 bars, ties
(hit both stop and target same bar) scored as a loss.

This repo has 30+ prior RSI-oversold variants but ALL use oscillator-based
exits (RSI>70) or SMA-based exits or time-stops -- none use this source's
fixed ATR bracket exit. Testing whether this distinct risk/reward exit
construction (rather than the entry logic itself) changes the profile
enough to pass validators, on QQQ/SPY/BTC/ETH daily bars (source used FX/
metals/indices/crypto with a 1.5*ATR stop / 3*ATR target and a 40-bar cap).

Signal logic
------------
- RSI(rsi_window=14): standard Wilder RSI.
- Entry (long): RSI crosses from <= oversold_thresh (default 30) up to
  > oversold_thresh (oversold-exit signal), entered at the FOLLOWING bar's
  open-equivalent (approximated here via the next bar's close return, since
  we operate on daily OHLC not next-bar-open fills like the source).
- Exit: whichever of (a) close hits the ATR-based stop (entry_price -
  atr_stop_mult*ATR(atr_window) at entry), (b) close hits the ATR-based
  target (entry_price + atr_stop_mult*rr_ratio*ATR(atr_window) at entry),
  or (c) max_hold_bars elapses (source's 40-bar walk-forward cap), comes
  first.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
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


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 14,
    oversold_thresh: float = 30.0,
    atr_window: int = 14,
    atr_stop_mult: float = 1.5,
    rr_ratio: float = 2.0,
    max_hold_bars: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rsi = _rsi(close, rsi_window)
    rsi_prev = rsi.shift(1)
    entry_signal = (rsi_prev <= oversold_thresh) & (rsi > oversold_thresh)

    atr = _atr(df, atr_window)

    close_vals = close.values
    atr_vals = atr.values
    entry_sig_vals = entry_signal.fillna(False).values

    n = len(close_vals)
    position_vals = np.zeros(n, dtype=int)

    in_position = False
    entry_idx = 0
    stop_price = 0.0
    target_price = 0.0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            price = close_vals[i]
            stop_hit = price <= stop_price
            target_hit = price >= target_price
            if stop_hit or target_hit or held >= max_hold_bars:
                in_position = False
                position_vals[i] = 0
                continue
            position_vals[i] = 1
        else:
            if bool(entry_sig_vals[i]) and atr_vals[i] == atr_vals[i]:  # not NaN
                in_position = True
                entry_idx = i
                entry_price = close_vals[i]
                stop_dist = atr_stop_mult * atr_vals[i]
                stop_price = entry_price - stop_dist
                target_price = entry_price + rr_ratio * stop_dist
                position_vals[i] = 1
            else:
                position_vals[i] = 0

    return pd.Series(position_vals, index=close.index, dtype=int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
