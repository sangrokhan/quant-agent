"""Strategy: HMA crossover gated by Sell-in-May/Halloween seasonal window.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Direct follow-up combining two prior results in this repo: (1) the accepted
HMA(100) single-line crossover (2026-09-09-013, both QQQ and SPY passing,
Sharpe 1.14/1.08), and (2) the rejected-but-near-miss Sell-in-May/Halloween
calendar seasonality (2026-09-09-019/020), whose own notes explicitly
suggested "combine the calendar window with an already-accepted
trend-following signal... instead of plain SMA, to recover Sharpe without
reintroducing MDD blowup." This iteration tests exactly that: take
long-only HMA(100) crossover positions, but ONLY while inside the
Nov(long_start_month)-Apr(long_end_month) seasonal window; flat outside it
regardless of the HMA signal. Hypothesis: restricting the already-accepted
trend-following entry to the historically stronger seasonal half of the
year should preserve (or improve) its Sharpe/MDD profile while reducing
time-in-market and whipsaw exposure during the weaker May-Oct window.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _wma(series: pd.Series, window: int) -> pd.Series:
    weights = pd.Series(range(1, window + 1), dtype=float)
    return series.rolling(window).apply(
        lambda x: (x * weights.values).sum() / weights.sum(), raw=True
    )


def _hma(close: pd.Series, hma_window: int) -> pd.Series:
    half_window = max(1, hma_window // 2)
    sqrt_window = max(1, round(math.sqrt(hma_window)))
    wma_half = _wma(close, half_window)
    wma_full = _wma(close, hma_window)
    raw_hma = 2 * wma_half - wma_full
    return _wma(raw_hma, sqrt_window)


def generate_signals(
    price_df: pd.DataFrame,
    hma_window: int = 80,
    long_start_month: int = 10,
    long_end_month: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series: HMA crossover positions,
    but only while inside the [long_start_month .. 12] U [1 .. long_end_month]
    seasonal "winter" window; flat outside it regardless of the HMA signal."""
    df = _prep(price_df)
    close = df["close"]
    hma = _hma(close, hma_window)

    above = close > hma
    entry = above & (~above.shift(1).fillna(False))
    exit_cross = (~above) & (above.shift(1).fillna(False))

    months = df.index.month
    if long_start_month <= long_end_month:
        in_window = (months >= long_start_month) & (months <= long_end_month)
    else:
        in_window = (months >= long_start_month) | (months <= long_end_month)
    in_window = pd.Series(in_window, index=df.index)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        window_ok = bool(in_window.iloc[i])
        if in_position:
            if bool(exit_cross.iloc[i]) or not window_ok:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if window_ok and bool(entry.iloc[i]):
                in_position = True
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
