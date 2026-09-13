"""Strategy: Donchian channel breakout entry with continuous ATR-relative
inverse position sizing.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per PineScriptForge's NQ Donchian Channel Breakout Backtest note
(https://pinescriptforge.com, browser_exec) and Lumley Trading's Turtle
N-unit sizing explainer: "Scale position size down during high-volatility
regimes (ATR exceeding 20-period average by 50%+) to maintain consistent
dollar risk." This iteration implements that as a CONTINUOUS sizing rule
(not the source's binary >50% trigger) on top of a Donchian(entry_window,
exit_window) breakout entry -- deliberately a DIFFERENT base construction
from every sizing-overlay strategy tested elsewhere in this repo (all of
which apply their risk-ratio to an SMA(200) trend gate). This tests
whether continuous ATR-relative-to-its-own-rolling-average inverse sizing
(exposure = clip(atr_reference / atr_relative, 0, leverage_cap), where
atr_relative = ATR(atr_period) / its own rolling atr_avg_window average)
improves on the repo's existing binary Donchian+ATR-filter variants
(2026-09-10-123, rejected) and plain Donchian breakouts (2026-09-04-054,
mixed) by keeping risk approximately constant in dollar terms rather than
gating entries on/off. First continuous-ATR-relative-sizing strategy in
this repo (existing ATR uses: binary filters, or fixed-multiple stop-loss
distances -- never a continuous inverse-sizing dial).

Signal logic
------------
- Entry: close breaks above its own rolling `entry_window`-day high
  (Donchian breakout, Turtle-style).
- Exit: close breaks below its own rolling `exit_window`-day low (asymmetric
  entry/exit lookback, standard Donchian Turtle convention).
- Between entry and exit, exposure is continuously scaled by ATR relative
  to its own rolling average: atr_relative = ATR(atr_period) /
  rolling_mean(ATR(atr_period), atr_avg_window); exposure =
  clip(atr_reference / atr_relative, 0, leverage_cap) -- i.e. when current
  volatility is elevated relative to its own recent average, exposure
  shrinks; when volatility subsides toward/below its average, exposure
  rises back up to (or above, capped) full size.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
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


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def _donchian_breakout_position(
    close: pd.Series, entry_window: int, exit_window: int
) -> pd.Series:
    """Turtle-style binary long/flat position: enter on new entry_window-day
    high, hold until a new exit_window-day low."""
    entry_high = close.rolling(entry_window).max().shift(1)
    exit_low = close.rolling(exit_window).min().shift(1)

    n = len(close)
    pos = np.zeros(n)
    in_position = False
    close_vals = close.to_numpy(dtype=float)
    entry_vals = entry_high.to_numpy(dtype=float)
    exit_vals = exit_low.to_numpy(dtype=float)

    for i in range(n):
        if not in_position:
            if not np.isnan(entry_vals[i]) and close_vals[i] > entry_vals[i]:
                in_position = True
        else:
            if not np.isnan(exit_vals[i]) and close_vals[i] < exit_vals[i]:
                in_position = False
        pos[i] = 1.0 if in_position else 0.0

    return pd.Series(pos, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    entry_window: int = 20,
    exit_window: int = 10,
    atr_period: int = 14,
    atr_avg_window: int = 20,
    atr_reference: float = 1.0,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    binary_position = _donchian_breakout_position(close, entry_window, exit_window)

    atr = _atr(df, atr_period)
    atr_avg = atr.rolling(atr_avg_window).mean()
    atr_relative = (atr / atr_avg.replace(0, np.nan)).astype(float)

    raw_exposure = (atr_reference / atr_relative).astype(float)
    exposure_scale = raw_exposure.clip(lower=0.0, upper=leverage_cap).fillna(0.0)

    position = binary_position * exposure_scale
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
