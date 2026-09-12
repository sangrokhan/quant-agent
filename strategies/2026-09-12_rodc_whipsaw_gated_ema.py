"""Strategy: EMA crossover trend-following gated by Poster's Rate of Directional
Change (RODC) whipsaw filter.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per Richard Poster's "Taming The Effects Of Whipsaw" (TASC March 2024, fully
disclosed Pine v5 source at
https://www.tradingview.com/script/z9IFUy5m-TASC-2024-03-Rate-of-Directional-Change/),
the Rate of Directional Change (RODC) counts ZigZag reversal segments within
a rolling lookback window: RODC = 100 * Segments / WindowSize. A higher RODC
means the window contains many alternating up/down segments (whipsaw,
choppy/ranging market); a lower RODC means fewer segments (a clean trend).
The source explicitly frames RODC as a WHIPSAW FILTER meant to suppress
false trend-following entries -- it discloses the indicator itself but no
concrete entry/exit rule, so this strategy adapts the source's own stated
purpose into a testable rule: a standard fast/slow EMA crossover
trend-following signal, gated flat unless RODC is below `rodc_max`
(a low-whipsaw/genuinely-trending regime). The source's original ZigZag
threshold is tick-based (forex pip units); here it is replaced with a
percentage price-change threshold (`zigzag_pct`) so the same construction
works for equity and crypto daily bars.

Signal logic
------------
- RODC(window, zigzag_pct): walk the trailing `window` closes; track
  alternating up/down "segments" -- a reversal is recorded when price moves
  against the current segment's direction by more than `zigzag_pct`.
  RODC = 100 * segment_count / window.
- Trend signal: EMA(fast) crosses above EMA(slow) -> raw long signal;
  crosses below -> raw flat signal.
- Final entry: raw long signal AND RODC <= rodc_max (low-whipsaw/trending
  regime); exit on raw flat signal OR RODC rising above rodc_max (regime
  flips choppy -- risk-off), OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
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


def _rodc_series(close: np.ndarray, window: int, zigzag_pct: float) -> np.ndarray:
    """Vectorized-per-bar (loop over bars, but O(window) each) RODC series."""
    n = len(close)
    rodc = np.full(n, np.nan)
    for i in range(window, n):
        seg = close[i - window : i + 1]  # length window+1, matches source's bkData+1 span
        mode_up = True
        n_ud = 1
        xext = seg[0]
        for j in range(1, len(seg)):
            xcls = seg[j]
            if not mode_up:
                if xext > xcls:
                    xext = xcls
                elif (xcls - xext) / xext >= zigzag_pct:
                    mode_up = True
                    n_ud += 1
                    xext = xcls
            else:
                if xext < xcls:
                    xext = xcls
                elif (xcls - xext) / xext <= -zigzag_pct:
                    mode_up = False
                    n_ud += 1
                    xext = xcls
        rodc[i] = 100.0 * n_ud / window
    return rodc


def generate_signals(
    price_df: pd.DataFrame,
    fast_ema: int = 10,
    slow_ema: int = 30,
    rodc_window: int = 30,
    zigzag_pct: float = 0.015,
    rodc_max: float = 40.0,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ema_fast = close.ewm(span=fast_ema, adjust=False).mean()
    ema_slow = close.ewm(span=slow_ema, adjust=False).mean()
    trend_up = ema_fast > ema_slow

    rodc = pd.Series(
        _rodc_series(close.to_numpy(dtype=float), rodc_window, zigzag_pct),
        index=close.index,
    )
    low_whipsaw = (rodc <= rodc_max) & rodc.notna()

    entry = trend_up & low_whipsaw
    exit_signal = (~trend_up) | (~low_whipsaw)

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
