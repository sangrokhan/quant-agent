"""Strategy: Supertrend computed on Heikin-Ashi OHLC, traded on real close prices.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-005):
Per TradingView user jordanfray's "Heikin Ashi Supertrend" script
(https://www.tradingview.com/script/9z16eauD-Heikin-Ashi-Supertrend/): the
standard ATR-based Supertrend indicator is computed using Heikin-Ashi OHLC
(instead of real OHLC) to generate smoother, less whipsaw-prone trend-flip
signals, but trades are entered/exited at REAL candle close prices (not the
synthetic HA prices) -- the source explicitly warns that trading directly on
HA prices produces unrealistic backtest results, and this construction is
meant to fix that while keeping the noise-reduction benefit of computing the
trend indicator itself on the smoothed HA series.

This is distinct from every prior Heikin-Ashi strategy already in this repo
(raw HA color-flip trend-following/mean-reversion, Vervoort's HACO zero-lag
-TEMA construction, EMA-crossover confirmed by HA candle color, HA-Smoothed
body-strength sizing dial) -- none of those compute a Supertrend indicator
ON TOP OF HA-transformed OHLC. It is also distinct from this repo's existing
plain (real-OHLC) Supertrend family.

Signal logic
------------
1. Compute Heikin-Ashi OHLC from real OHLC:
   haClose = (O+H+L+C)/4
   haOpen[0] = (O[0]+C[0])/2 ; haOpen[t] = (haOpen[t-1]+haClose[t-1])/2
   haHigh = max(H, haOpen, haClose) ; haLow = min(L, haOpen, haClose)
2. Compute standard ATR(atr_window) Supertrend bands on the HA OHLC series
   (basic upper/lower bands = hl2_ha +/- multiplier*ATR_ha, with the usual
   Supertrend band-tightening/trend-flip recursion).
3. Long when the HA-based Supertrend flips to bullish (trend flag flips
   from -1 to +1); exit (flat) when it flips back to bearish.
4. Position is applied to REAL daily returns (close-to-close), NOT
   HA-close-to-HA-close returns -- this is the source's specific fix for
   backtest-realism.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
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


def _heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    ha_close = (o + h + l + c) / 4.0
    ha_open = pd.Series(index=df.index, dtype=float)
    ha_open.iloc[0] = (o.iloc[0] + c.iloc[0]) / 2.0
    for i in range(1, len(df)):
        ha_open.iloc[i] = (ha_open.iloc[i - 1] + ha_close.iloc[i - 1]) / 2.0
    ha_high = pd.concat([h, ha_open, ha_close], axis=1).max(axis=1)
    ha_low = pd.concat([l, ha_open, ha_close], axis=1).min(axis=1)
    return pd.DataFrame(
        {"open": ha_open, "high": ha_high, "low": ha_low, "close": ha_close},
        index=df.index,
    )


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    tr = pd.concat(
        [(h - l), (h - prev_c).abs(), (l - prev_c).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def _supertrend_direction(ha_df: pd.DataFrame, atr_window: int, multiplier: float) -> pd.Series:
    hl2 = (ha_df["high"] + ha_df["low"]) / 2.0
    atr = _atr(ha_df, atr_window)
    basic_upper = hl2 + multiplier * atr
    basic_lower = hl2 - multiplier * atr

    n = len(ha_df)
    final_upper = np.full(n, np.nan)
    final_lower = np.full(n, np.nan)
    direction = np.ones(n, dtype=int)  # 1 = bullish, -1 = bearish
    close = ha_df["close"].values
    bu = basic_upper.values
    bl = basic_lower.values

    for i in range(n):
        if i == 0 or np.isnan(bu[i - 1]) or np.isnan(final_upper[i - 1]):
            final_upper[i] = bu[i]
            final_lower[i] = bl[i]
            direction[i] = 1 if not np.isnan(close[i]) and not np.isnan(bl[i]) and close[i] > bl[i] else -1
            continue

        final_upper[i] = (
            bu[i] if (bu[i] < final_upper[i - 1] or close[i - 1] > final_upper[i - 1]) else final_upper[i - 1]
        )
        final_lower[i] = (
            bl[i] if (bl[i] > final_lower[i - 1] or close[i - 1] < final_lower[i - 1]) else final_lower[i - 1]
        )

        if direction[i - 1] == 1:
            direction[i] = -1 if close[i] < final_lower[i] else 1
        else:
            direction[i] = 1 if close[i] > final_upper[i] else -1

    return pd.Series(direction, index=ha_df.index)


def generate_signals(
    price_df: pd.DataFrame,
    atr_window: int = 10,
    multiplier: float = 3.0,
) -> pd.Series:
    df = _prep(price_df)
    ha_df = _heikin_ashi(df)
    direction = _supertrend_direction(ha_df, atr_window=atr_window, multiplier=multiplier)
    position = (direction == 1).astype(int)
    return position.reindex(df.index).fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    atr_window: int = 10,
    multiplier: float = 3.0,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)
    position = generate_signals(price_df, atr_window=atr_window, multiplier=multiplier)
    # trade on REAL close-to-close returns, signal decided at prior bar's close
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
