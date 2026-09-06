"""Strategy: Hull Moving Average (HMA) slope-turn trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-128):
Alan Hull's HMA formula (per ThinkMarkets' write-up, corroborated by
TradingView/usethinkscript/Scribd SERP snippets on the "color change" HMA
strategy): HMA(n) = WMA(2*WMA(price, n/2) - WMA(price, n), round(sqrt(n))).
The commonly cited mechanical trading rule (per usethinkscript forum and the
Scribd HMA strategy summary read via SERP): go long when the HMA's slope
turns from falling to rising (the "color change" moment most HMA chart
indicators visualize), and exit/go flat when the slope turns back down.
This is a genuinely different construction from every prior moving-average
strategy in this repo -- HMA is not a simple/exponential/adaptive/Kaufman
moving average, it is Hull's specific WMA-of-WMA-difference-with-sqrt-period
smoothing formula designed explicitly to reduce lag versus SMA/EMA while
staying smooth (distinct from KAMA/adaptive-MA's volatility-based smoothing
constant, and distinct from the plain SMA/EMA crossover strategies already
tested).

Source: https://www.thinkmarkets.com/en/trading-academy/forex/hull-moving-average/
(formula, read via browser_exec after web_search errored on this
iteration's query) plus corroborating SERP snippets on the slope-turn entry
rule (Scribd "Hull Moving Average Trading Strategy" summary, usethinkscript
forum thread on coding the color-change signal) since the primary sources
those SERP results point to were not independently re-fetched.

Signal logic
------------
- HMA(hma_window) computed via the standard formula above.
- Entry (long): HMA's `slope_confirm_days`-bar-ago value was falling
  (HMA[t-1] < HMA[t-2]) and it just turned to rising (HMA[t] > HMA[t-1]) --
  the slope-turn / "color change" moment.
- Exit: HMA slope turns back down (HMA[t] < HMA[t-1] after HMA[t-1] >=
  HMA[t-2]), OR a `max_hold_days` time-stop (added robustness cap, not in
  the original simple rule, to avoid indefinite holds through a long
  perfectly-monotonic HMA run with no down-tick).
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _wma(series: pd.Series, window: int) -> pd.Series:
    weights = np.arange(1, window + 1, dtype=float)

    def _w(x):
        return float(np.dot(x, weights) / weights.sum())

    return series.rolling(window).apply(_w, raw=True)


def _hma(series: pd.Series, window: int) -> pd.Series:
    half_window = max(int(window / 2), 1)
    sqrt_window = max(int(round(window ** 0.5)), 1)
    wma_half = _wma(series, half_window)
    wma_full = _wma(series, window)
    diff = 2 * wma_half - wma_full
    return _wma(diff, sqrt_window)


def generate_signals(
    price_df: pd.DataFrame,
    hma_window: int = 20,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    hma = _hma(close, hma_window)
    hma_prev = hma.shift(1)
    hma_prev2 = hma.shift(2)

    was_falling = hma_prev < hma_prev2
    now_rising = hma > hma_prev
    entry = was_falling.fillna(False) & now_rising.fillna(False)

    was_rising_or_flat = hma_prev >= hma_prev2
    now_falling = hma < hma_prev
    exit_slope_down = was_rising_or_flat.fillna(False) & now_falling.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_slope_down.iloc[i]) or held >= max_hold_days:
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
