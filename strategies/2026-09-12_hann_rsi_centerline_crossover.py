"""Strategy: Ehlers "Improved RSI w/ Hann Windowing" zero-centerline crossover.

Source: TASC (Technical Analysis of Stocks & Commodities) January 2022
Traders' Tips, John Ehlers "(Yet Another Improved) RSI Enhanced With Hann
Windowing", via TradingView scripts index
https://www.tradingview.com/scripts/tasc/page-3/ (visited 2026-09-12, see
knowledge_base/visited_pages.jsonl).

Source's disclosed construction:
    Starts from Wilder's classic "closes up" (CU) / "closes down" (CD)
    per-bar values (CU = max(close-close[1], 0), CD = max(close[1]-close, 0)),
    same inputs as the original 1978 RSI. Instead of Wilder's IIR
    (exponential) smoothing of CU/CD, apply a Hann-window FIR filter (finite
    impulse response, weights = 1 - cos(2*pi*(k+1)/(N+1)) for k=0..N-1,
    normalized to sum to 1) separately to the CU and CD series over a
    rolling `length`-bar window. The enhanced RSI is then:
        hann_rsi = (filtered_CU - filtered_CD) / (filtered_CU + filtered_CD)
    which is confined to [-1, +1] with a 0.0 centerline (vs Wilder's [0,100]
    with a 50 centerline). Source's own stated interpretation: values above
    the 0.0 centerline are an "overvalued" region, below is "undervalued".

Operationalized here as a long-only centerline-crossover trend/momentum
strategy: long entry when hann_rsi crosses above 0 (momentum turning
positive), exit when it crosses back below 0, or a max_hold_days time-stop.

Novelty vs prior KB entries: this repo has many RSI(0-100)/50-centerline
strategies (e.g. 2026-09-04-077, 2026-09-04-165), but none use Ehlers' Hann
FIR-windowed smoothing in place of Wilder's IIR averaging -- the FIR window
materially changes the indicator's lag/smoothness/whipsaw characteristics
(finite memory vs infinite exponential memory), which is exactly the kind of
distinct technical construction this repo treats as novel (c.f. the many
SuperSmoother/roofing-filter variants that also differ only in their
smoothing technique).

Interface contract (see validation/grid_test.py, validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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


def _hann_weights(length: int) -> np.ndarray:
    k = np.arange(1, length + 1)
    w = 1 - np.cos(2 * np.pi * k / (length + 1))
    return w / w.sum()


def _hann_filter(series: pd.Series, length: int) -> pd.Series:
    weights = _hann_weights(length)
    vals = series.values
    n = len(vals)
    out = np.full(n, np.nan)
    for i in range(length - 1, n):
        window = vals[i - length + 1 : i + 1]
        out[i] = np.dot(window, weights)
    return pd.Series(out, index=series.index)


def _hann_rsi(close: pd.Series, length: int) -> pd.Series:
    delta = close.diff()
    cu = delta.clip(lower=0).fillna(0.0)
    cd = (-delta.clip(upper=0)).fillna(0.0)

    filtered_cu = _hann_filter(cu, length)
    filtered_cd = _hann_filter(cd, length)

    denom = filtered_cu + filtered_cd
    hann_rsi = (filtered_cu - filtered_cd) / denom.replace(0, np.nan)
    return hann_rsi.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    length: int = 14,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    hann_rsi = _hann_rsi(close, length)

    entry = (hann_rsi > 0) & (hann_rsi.shift(1) <= 0)
    exit_signal = (hann_rsi < 0) & (hann_rsi.shift(1) >= 0)

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
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
