"""Strategy: Volatility-Based Momentum (VBM) threshold trend entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-066):
Per Steve Roehling's "A Volatility Based Momentum Indicator for Traders"
(Medium, Nov 2018): VBM(n,v) = (Close - Close[n periods ago]) / ATR(v
periods) -- a variation on the Rate-of-Change indicator that divides the
RAW PRICE DIFFERENCE (not a percentage) by the Average True Range,
expressing momentum in "multiples of volatility" (MoV) rather than
percentage terms. The source's stated benefit is that MoV normalizes
momentum across different securities/volatility regimes using an ATR
(range-based) denominator rather than a standard-deviation-of-returns
denominator.

This is mechanically distinct from the already-tested (and rejected)
volatility-adjusted momentum strategy in this repo (2026-09-08-065, which
divides ANNUALIZED PERCENTAGE RETURN by REALIZED VOLATILITY, i.e. a
Sharpe-like return/std-of-returns ratio) -- VBM instead divides the RAW
PRICE-LEVEL DIFFERENCE by ATR (a range-based, not standard-deviation-
based, volatility proxy), a materially different normalization that
reacts differently to gap-heavy vs. smooth-drift price paths. Also
distinct from every prior ATR-normalized strategy in this repo (Keltner/
STARC/Chandelier/ATR-expansion band constructions all use ATR as a BAND
WIDTH around price, never as a momentum-normalization DENOMINATOR for a
raw price-difference numerator).

Long entry: VBM(momentum_window, atr_window) crosses above
entry_threshold (a positive multiple of ATR, e.g. 1.0 = price has moved up
by one full ATR unit over the window -- source's own suggested
interpretation scale). Exit: VBM crosses back below exit_threshold (source
implies VBM behaves like ROC for interpretation purposes, so a
zero/near-zero exit threshold mirrors typical ROC zero-line exit
conventions) or a max_hold_days time-stop.

Source: https://medium.com/@sroehling/a-volatility-based-momentum-indicator-for-traders-250957de978d

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
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
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    momentum_window: int = 22,
    atr_window: int = 65,
    entry_threshold: float = 1.0,
    exit_threshold: float = 0.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    atr = _atr(df, atr_window)
    price_diff = close - close.shift(momentum_window)
    vbm = (price_diff / atr.replace(0, np.nan)).fillna(0.0)

    entry = vbm >= entry_threshold
    exit_signal = vbm < exit_threshold

    entry_arr = entry.to_numpy(dtype=bool)
    exit_arr = exit_signal.to_numpy(dtype=bool)

    position = np.zeros(n, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_arr[i]) or held >= max_hold_days:
                in_position = False
                position[i] = 0
                continue
            position[i] = 1
        else:
            if bool(entry_arr[i]):
                in_position = True
                entry_idx = i
                position[i] = 1
            else:
                position[i] = 0

    return pd.Series(position, index=close.index, dtype=int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    # Shift position by 1 day: yesterday's signal determines today's return
    # exposure (avoid look-ahead bias -- can't trade on today's own close).
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
