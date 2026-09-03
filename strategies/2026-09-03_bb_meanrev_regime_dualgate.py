"""Strategy: Bollinger-Band mean reversion gated by a DUAL regime filter
(ATR-percentile volatility gate + moving-average slope-flatness trend gate).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-03-023):
Source (vantixs.com mean-reversion crypto template) claims a mean-reversion
entry (price touches/closes below the lower Bollinger Band, or z-score <
-2) only has edge when BOTH (a) volatility is NOT expanding (ATR(14) below
its own 75th percentile over a trailing 90-period window) AND (b) the market
is genuinely range-bound, not trending (the slope of a 50-period SMA is
within +/-0.1% per bar). The source reports their own backtest found this
dual gate cut max drawdown from 32% to 11% while only giving up ~15% of
returns, vs an ungated version.

This is distinct from the previously-rejected 2026-09-03-001 QQQ BB
mean-reversion strategy, which used a SINGLE gate (realized-vol vs its own
trailing-1yr median) and was tested only on QQQ (Sharpe -0.30, decisive
reject). Here we test a genuinely different two-part gate mechanism
(ATR-percentile + trend-slope-flatness, not realized-vol-vs-median) across
BOTH equity and crypto.

Signal logic
------------
- ATR(14) percentile-gate: current ATR(14) is at or below the
  ``atr_percentile_threshold`` (default 0.75) percentile of its own trailing
  ``atr_lookback`` (default 90) window -> volatility is NOT expanding.
- Trend-slope-gate: the percent change of a ``ma_window`` (default 50)
  period SMA over the last ``slope_window`` (default 1) bar(s) has absolute
  value <= ``slope_threshold`` (default 0.001, i.e. 0.1%/bar) -> market is
  range-bound, not trending.
- Entry (long): close < lower Bollinger Band (``bb_window``, ``bb_std``)
  AND both gates are active.
- Exit: close crosses back above the ``bb_window`` SMA (mean-reversion
  target reached), OR either gate flips off (risk-off exit), OR after
  ``max_hold_days`` bars (avoid indefinite holds).
- Flat otherwise.

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


def _true_range(df: pd.DataFrame) -> pd.Series:
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
    return tr


def generate_signals(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    atr_window: int = 14,
    atr_lookback: int = 90,
    atr_percentile_threshold: float = 0.75,
    ma_window: int = 50,
    slope_window: int = 1,
    slope_threshold: float = 0.001,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()
    lower_band = sma - bb_std * std

    tr = _true_range(df)
    atr = tr.rolling(atr_window).mean()
    # Rolling percentile-rank of current ATR within its own trailing window
    # (causal: uses only past atr_lookback bars, no look-ahead). Vectorized
    # via a plain numpy loop over the (small) trailing lookback slice
    # instead of rolling().apply(raw=False), which is far too slow at scale.
    import numpy as np

    atr_vals = atr.to_numpy()
    n = len(atr_vals)
    atr_pct_rank = np.full(n, np.nan)
    if n >= atr_window:
        for i in range(atr_window - 1, n):
            start = max(0, i - atr_lookback + 1)
            window = atr_vals[start : i + 1]
            cur = atr_vals[i]
            if np.isnan(cur) or len(window) == 0:
                continue
            valid = window[~np.isnan(window)]
            if len(valid) == 0:
                continue
            atr_pct_rank[i] = float((valid <= cur).mean())
    atr_pct_rank = pd.Series(atr_pct_rank, index=atr.index)
    vol_gate = atr_pct_rank <= atr_percentile_threshold

    trend_ma = close.rolling(ma_window).mean()
    ma_slope = trend_ma.pct_change(slope_window)
    trend_gate = ma_slope.abs() <= slope_threshold

    both_gates = vol_gate.fillna(False) & trend_gate.fillna(False)

    entry = (close < lower_band) & both_gates
    exit_meanrev = close > sma
    exit_gate_flip = ~both_gates

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or bool(exit_gate_flip.iloc[i]) or held >= max_hold_days:
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
