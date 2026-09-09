"""Strategy: Chandelier Exit + Supertrend dual-confirmation trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-090):
Per Google's AI-overview of the "Chandelier Exit combined with Supertrend"
dual-confirmation approach (accessed via browser_exec fallback -- web_search's
DDGS backend errored with a TLS connection error): "It uses two
volatility-based indicators to filter out market noise and capture strong
macro trends... must be bullish for a buy signal." Both indicators are
already tested standalone/gated in this repo (Chandelier trend-flip
2026-09-09-064/065; Supertrend flip 2026-09-04-053, Supertrend+RSI
2026-09-06-*, Supertrend+Choppiness/vol-regime 2026-09-09-07x) but never
combined as a simultaneous dual-AND-gate confirmation system, which is the
source's own distinct operational rule (both indicators must independently
agree bullish, not one filtering the other's entry trigger).

Signal logic
------------
- Chandelier long_stop: Highest(High, chand_period) - chand_multiplier*ATR
  (chand_period), ratcheting up only while price stays above it (same
  construction as 2026-09-09_chandelier_exit_trendflip.py).
- Supertrend bullish regime: standard Olivier Seban Supertrend construction
  (HL2 +/- st_multiplier*ATR(st_period) bands with stop-and-reverse flip),
  same construction as 2026-09-04_supertrend_flip.py.
- Entry (long): close > Chandelier long_stop AND Supertrend is bullish,
  triggered on the bar this combined condition FIRST becomes true (i.e.
  either indicator just flipped bullish while the other was already
  bullish, or both flip on the same bar) -- the dual-confirmation entry per
  source.
- Exit: EITHER indicator turns bearish (close crosses below Chandelier
  long_stop, OR Supertrend flips bearish) -- source's own "must be bullish
  for both" implies exit as soon as either disagrees -- or a max_hold_days
  time-stop.
- Flat otherwise.

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
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def _chandelier_bullish(df: pd.DataFrame, period: int, multiplier: float) -> pd.Series:
    highest_high = df["high"].rolling(period).max()
    atr = _atr(df, period)
    raw_stop = highest_high - multiplier * atr

    close = df["close"].to_numpy()
    raw = raw_stop.to_numpy()
    n = len(df)
    stop = np.full(n, np.nan)

    for i in range(n):
        if np.isnan(raw[i]):
            continue
        if i == 0 or np.isnan(stop[i - 1]):
            stop[i] = raw[i]
            continue
        if close[i - 1] > stop[i - 1]:
            stop[i] = max(raw[i], stop[i - 1])
        else:
            stop[i] = raw[i]

    long_stop = pd.Series(stop, index=df.index)
    return (df["close"] > long_stop).fillna(False)


def _supertrend_bullish(df: pd.DataFrame, atr_period: int, multiplier: float) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    hl2 = (high + low) / 2.0
    atr = _atr(df, atr_period)
    basic_upper = hl2 + multiplier * atr
    basic_lower = hl2 - multiplier * atr

    idx = df.index
    final_upper = pd.Series(index=idx, dtype=float)
    final_lower = pd.Series(index=idx, dtype=float)
    bullish = pd.Series(index=idx, dtype=bool)

    first_valid_pos = atr.first_valid_index()
    if first_valid_pos is None:
        return pd.Series(False, index=idx)
    start_pos = list(idx).index(first_valid_pos)

    final_upper.iloc[start_pos] = basic_upper.iloc[start_pos]
    final_lower.iloc[start_pos] = basic_lower.iloc[start_pos]
    bullish.iloc[start_pos] = close.iloc[start_pos] > final_upper.iloc[start_pos]

    for i in range(start_pos + 1, len(idx)):
        bu = basic_upper.iloc[i]
        bl = basic_lower.iloc[i]
        prev_fu = final_upper.iloc[i - 1]
        prev_fl = final_lower.iloc[i - 1]
        prev_close = close.iloc[i - 1]

        fu = bu if (bu < prev_fu or prev_close > prev_fu) else prev_fu
        fl = bl if (bl > prev_fl or prev_close < prev_fl) else prev_fl
        final_upper.iloc[i] = fu
        final_lower.iloc[i] = fl

        prev_bull = bullish.iloc[i - 1]
        cur_close = close.iloc[i]
        if prev_bull:
            bullish.iloc[i] = cur_close > fl
        else:
            bullish.iloc[i] = cur_close > fu

    return bullish.fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    chand_period: int = 22,
    chand_multiplier: float = 3.0,
    st_period: int = 10,
    st_multiplier: float = 3.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    chand_bull = _chandelier_bullish(df, period=chand_period, multiplier=chand_multiplier)
    st_bull = _supertrend_bullish(df, atr_period=st_period, multiplier=st_multiplier)

    both_bullish = (chand_bull & st_bull).to_numpy()
    n = len(df)
    pos_arr = np.zeros(n, dtype=int)

    in_pos = False
    entry_idx = -1
    for i in range(n):
        if in_pos:
            held = i - entry_idx
            if (not both_bullish[i]) or held >= max_hold_days:
                in_pos = False
            else:
                pos_arr[i] = 1
        if not in_pos and both_bullish[i] and (i == 0 or not both_bullish[i - 1]):
            in_pos = True
            entry_idx = i
            pos_arr[i] = 1

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
