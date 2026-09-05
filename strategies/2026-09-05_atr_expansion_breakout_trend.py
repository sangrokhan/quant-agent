"""Strategy: ATR-expansion volatility breakout with trend filter and
mean-reversion exit ("Volatility ATR Bands" family).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-055):
Per quantifiedstrategies.com's "Volatility ATR Bands Strategy With a
33-Year Backtest" article, the system's three entry rules are: (1) a
VOLATILITY rule -- ATR itself surges (jumps sharply above its own recent
average), signaling volatility expansion; (2) a PRICE-ACTION rule -- price
breaks above the upper ATR/Keltner-style band (EMA + atr_mult*ATR) after
that expansion; (3) a TREND FILTER -- price above a longer-term SMA. The
exit is a MEAN-REVERSION signal: price crossing back through the channel
centerline (the EMA basis).

This is mechanically distinct from every prior Keltner/ATR strategy already
tested in this repo (2026-09-03-016 plain Keltner breakout, 2026-09-04-091/
126 TTM/LazyBear squeeze-release, 2026-09-04-116 Chande Kroll, 2026-09-04-
132 FRAMA+ATR-band, 2026-04-092 dual-ROC+ATR-stop): none of those use the
raw ATR VALUE crossing above its own rolling average as an explicit entry
gate -- they either react purely to price crossing a static band, or to a
Bollinger-vs-Keltner squeeze/release. Here, entry requires the ATR-expansion
condition to be true independently of (and in addition to) the price
breaking the upper band, which is the source's distinguishing design
choice.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

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
    ema_window: int = 20,
    atr_window: int = 14,
    atr_mult: float = 2.0,
    atr_expansion_avg_window: int = 20,
    atr_expansion_ratio: float = 1.25,
    trend_sma_window: int = 200,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry (long) requires ALL three of:
      1. Volatility expansion: current ATR(atr_window) >= atr_expansion_ratio
         times its own rolling `atr_expansion_avg_window`-day average.
      2. Price action: close breaks above the upper ATR/Keltner-style band
         (EMA(ema_window) + atr_mult * ATR(atr_window)).
      3. Trend filter: close > SMA(trend_sma_window).
    Exit: close crosses back below the EMA basis (mean-reversion signal),
    OR the trend filter breaks (close <= SMA(trend_sma_window)), OR a
    max_hold_days time-stop.
    """
    df = _prep(price_df)
    close = df["close"]

    ema = close.ewm(span=ema_window, adjust=False).mean()
    atr = _atr(df, atr_window)
    atr_avg = atr.rolling(atr_expansion_avg_window).mean()
    upper_band = ema + atr_mult * atr
    trend_sma = close.rolling(trend_sma_window).mean()

    vol_expansion = atr >= (atr_avg * atr_expansion_ratio)
    price_breakout = close > upper_band
    trend_ok = close > trend_sma

    entry = vol_expansion.fillna(False) & price_breakout.fillna(False) & trend_ok.fillna(False)
    exit_meanrev = close < ema
    exit_trend_break = ~trend_ok.fillna(False)

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
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
