"""Strategy: Jurik Moving Average (JMA) / DWMA crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-099):
Per Google AI-overview synthesis (Trading with DaviddTech/LuxAlgo
sources, query "Jurik Moving Average JMA crossover trading strategy
exact entry exit rules"): a fast JMA line (length 7) crossing above a
slower Double-Weighted Moving Average (DWMA, length 30) signals a long
entry (crossover confirmed by the fast line's upward slope); exit
primarily on the reverse crossover (fast line crosses back below the
slow line), backstopped by an ATR-based stop-loss.

Mark Jurik's actual JMA algorithm is proprietary/closed-source (adaptive
smoothing + phase correction, not publicly disclosed in exact
coefficient form). This strategy uses a well-documented PUBLIC
approximation: a double-EMA-smoothed line (EMA of EMA, which
meaningfully reduces lag vs. a single EMA while remaining much less
noisy than raw price, capturing JMA's core "low lag + low noise" design
goal) stands in for the fast JMA(7) line. DWMA (Double-Weighted Moving
Average = WMA of WMA, a well-defined public formula, unlike JMA) is
implemented exactly per its standard definition for the slow(30) line.

First Jurik-family / DWMA-crossover strategy in this repo (0 prior hits
on "Jurik"/"JMA") -- distinct from all other MA-crossover variants
already tested (SMA/EMA/HMA/KAMA/TEMA/FRAMA/T3/McGinley/Zero-Lag) since
DWMA (double-weighted MA) has not been used as the slow line in any
prior crossover strategy here.

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


def _double_ema(close: pd.Series, span: int) -> pd.Series:
    """Public JMA approximation: EMA-of-EMA (reduces lag vs single EMA)."""
    ema1 = close.ewm(span=span, adjust=False).mean()
    ema2 = ema1.ewm(span=span, adjust=False).mean()
    return ema2


def _wma(series: pd.Series, window: int) -> pd.Series:
    weights = pd.Series(range(1, window + 1), dtype=float)
    return series.rolling(window).apply(
        lambda x: (x * weights.values).sum() / weights.sum(), raw=True
    )


def _dwma(close: pd.Series, window: int) -> pd.Series:
    """Double-Weighted Moving Average: WMA of WMA."""
    wma1 = _wma(close, window)
    wma2 = _wma(wma1, window)
    return wma2


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


def generate_signals(
    price_df: pd.DataFrame,
    fast_span: int = 7,
    slow_window: int = 30,
    atr_window: int = 14,
    atr_mult: float = 1.5,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fast_jma = _double_ema(close, fast_span)
    slow_dwma = _dwma(close, slow_window)
    atr = _atr(df, atr_window)

    fast_above = fast_jma > slow_dwma
    fast_rising = fast_jma > fast_jma.shift(1)
    entry = fast_above & (~fast_above.shift(1).fillna(False)) & fast_rising
    exit_cross = ~fast_above

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
