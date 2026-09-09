"""Strategy: Double Stochastic agreement (fast+slow), oversold-zone bullish
crossover, 50-MA trend filter (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-070):
Per The Forex Geek's "Double Stochastic Strategy"
(https://theforexgeek.com/double-stochastic-strategy/, browser_exec
fallback -- web_search DDGS returned no results for several direct
queries), the source's own disclosed buy rule requires TWO plain %K/%D
stochastic oscillators of DIFFERENT lookback periods (a fast 5,3,3 and a
slow 10,3,3) to simultaneously: (1) both have %K crossing above %D
(bullish cross), (2) both be near the oversold 20 zone, while (3) price is
above a 50-period moving average (trend filter). The dual-timeframe
agreement requirement -- both a fast and a slow stochastic must confirm
the same oversold-bounce signal at the same time -- is distinct from every
existing stochastic strategy in this repo (all of which use a single
stochastic/StochRSI, or an Ehlers/Fisher-transformed variant, never two
plain stochastics of different periods required to agree).

Signal logic
------------
- Stochastic %K/%D (fast, period fast_k_window/fast_d_window) and (slow,
  period slow_k_window/slow_d_window), standard formula:
      %K = 100 * (close - LL_n) / (HH_n - LL_n)   (LL/HH = n-bar low/high)
      %D = SMA(%K, d_window)
- Trend filter: close > SMA(trend_window).
- Oversold zone: both %K_fast and %K_slow <= oversold_threshold at the bar
  immediately before the bullish cross (i.e. the cross originates from the
  oversold zone).
- Entry (long): %K_fast crosses above %D_fast AND %K_slow crosses above
  %D_slow on the SAME bar AND both were in the oversold zone the bar
  before AND trend filter is satisfied.
- Exit: EITHER stochastic's %K crosses back below its %D (loss of
  agreement/momentum), OR close drops below the trend SMA (structure
  break), OR a `max_hold_days` time-stop (source doesn't specify one;
  this repo consistently adds a safety-net time-stop).
- Flat otherwise; long-only, no shorting (per repo convention / SAFETY.md).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly across a parameter grid).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _stochastic(df: pd.DataFrame, k_window: int, d_window: int) -> tuple[pd.Series, pd.Series]:
    high, low, close = df["high"], df["low"], df["close"]
    ll = low.rolling(k_window).min()
    hh = high.rolling(k_window).max()
    rng = (hh - ll).replace(0, pd.NA)
    k = 100.0 * (close - ll) / rng
    k = k.fillna(50.0)
    d = k.rolling(d_window).mean()
    return k, d


def generate_signals(
    price_df: pd.DataFrame,
    fast_k_window: int = 5,
    fast_d_window: int = 3,
    slow_k_window: int = 10,
    slow_d_window: int = 3,
    trend_window: int = 50,
    oversold_threshold: float = 25.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    k_fast, d_fast = _stochastic(df, fast_k_window, fast_d_window)
    k_slow, d_slow = _stochastic(df, slow_k_window, slow_d_window)

    trend_sma = close.rolling(trend_window).mean()
    trend_gate = close > trend_sma

    cross_fast = (k_fast > d_fast) & (k_fast.shift(1) <= d_fast.shift(1))
    cross_slow = (k_slow > d_slow) & (k_slow.shift(1) <= d_slow.shift(1))

    was_oversold_fast = k_fast.shift(1) <= oversold_threshold
    was_oversold_slow = k_slow.shift(1) <= oversold_threshold

    entry = (
        cross_fast
        & cross_slow
        & was_oversold_fast.fillna(False)
        & was_oversold_slow.fillna(False)
        & trend_gate.fillna(False)
    )

    exit_cross_fast = (k_fast < d_fast) & (k_fast.shift(1) >= d_fast.shift(1))
    exit_cross_slow = (k_slow < d_slow) & (k_slow.shift(1) >= d_slow.shift(1))
    exit_signal = exit_cross_fast | exit_cross_slow
    exit_trend_break = close < trend_sma

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
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
