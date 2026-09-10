"""Strategy: Aroon Oscillator entry trigger + Chandelier Exit trailing stop
(dual-indicator trend-following combo).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-125):
Per a Google AI-overview synthesis (StockCharts.com/LuxAlgo/FxDailyReport
et al) via browser_exec Google SERP fallback of "Aroon Oscillator Chandelier
exit combo strategy": the Aroon Oscillator ("entry engine" -- measures time
elapsed since a new high/low over a 25-period lookback, filtering out
sideways noise, firing only on directional breakouts) triggers the entry
while the Chandelier Exit (ATR-based trailing stop = Highest High over N
bars minus atr_mult x ATR) both confirms the breakout (close must close
firmly above the Chandelier line) and supplies the trailing stop-loss for
the trade's whole duration. Source's disclosed rules: (1) Aroon Oscillator
crosses above 0, ideally pushing past +50 (trend confirmation); (2) close
must close firmly above the Chandelier Exit line (which flips from
red/above-price to green/below-price); (3) enter at the close of that
breakout candle; (4) exit when a candle closes back below the (ratcheting)
Chandelier Exit line.

This is a distinct combination from prior Chandelier-family entries in this
repo: 2026-09-04-035 (Chandelier regime + StochRSI dip-buy TIMING, not an
Aroon breakout entry), 2026-09-09-064/065 (standalone Chandelier trend-flip,
no Aroon), 2026-09-09-090/091 (Chandelier + Supertrend dual-confirm,
accepted QQQ -- different second indicator entirely). Also distinct from
prior Aroon-family entries (2026-09-04-031/063, 2026-09-05-079,
2026-09-06-098, 2026-09-09-082 -- none paired Aroon with a Chandelier Exit
trailing stop; 2026-09-06-098 paired Aroon with ADX instead).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
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


def _aroon_oscillator(df: pd.DataFrame, window: int) -> pd.Series:
    import numpy as np

    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    n = len(high)

    aroon_up = np.full(n, np.nan)
    aroon_down = np.full(n, np.nan)

    if n >= window:
        high_windows = np.lib.stride_tricks.sliding_window_view(high, window)
        low_windows = np.lib.stride_tricks.sliding_window_view(low, window)
        periods_since_high = window - 1 - high_windows.argmax(axis=1)
        periods_since_low = window - 1 - low_windows.argmin(axis=1)
        aroon_up[window - 1 :] = 100 * (window - periods_since_high) / window
        aroon_down[window - 1 :] = 100 * (window - periods_since_low) / window

    return pd.Series(aroon_up - aroon_down, index=df.index)


def _chandelier_exit(df: pd.DataFrame, window: int, atr_mult: float) -> pd.Series:
    atr = _atr(df, window)
    highest_high = df["high"].rolling(window).max()
    return highest_high - atr_mult * atr


def generate_signals(
    price_df: pd.DataFrame,
    aroon_window: int = 25,
    aroon_entry_threshold: float = 50.0,
    chandelier_window: int = 22,
    chandelier_atr_mult: float = 3.0,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    aroon_osc = _aroon_oscillator(df, aroon_window)
    chandelier = _chandelier_exit(df, chandelier_window, chandelier_atr_mult)

    entry = (aroon_osc > aroon_entry_threshold) & (close > chandelier) & chandelier.notna()
    exit_break = (close < chandelier) & chandelier.notna()

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_break.iloc[i]) or held >= max_hold_days:
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
