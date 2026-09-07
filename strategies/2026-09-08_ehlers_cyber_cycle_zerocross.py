"""Strategy: Ehlers Cyber Cycle zero-line crossover trend/cycle strategy --
long only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-013):
Per John Ehlers' exact formula (Cybernetic Analysis for Stocks and Futures,
2004), as documented at
https://help.ctrader.com/indicators/built-in/oscillators/cyber-cycle/: the
Cyber Cycle applies a 4-bar weighted smoothing to the median price, then a
2-pole recursive high-pass-like filter (parameterized by alpha, default
0.07) to isolate the cyclic component with minimal lag. A Trigger line
(Cycle lagged by 1 bar) crossing the Cycle line, or the Cycle line's own
zero-line crossover, are the source's documented trading rules ("crossing
above zero signals a potential uptrend... crossing below zero signals a
potential downtrend"). This strategy tests the zero-line-crossover rule
(long entry) combined with the Cycle/Trigger crossover as the exit trigger,
since Ehlers designed Trigger specifically to give an earlier turning-point
signal than a raw zero-cross. First Ehlers Cyber Cycle strategy in this
repo -- distinct from all other Ehlers-family strategies already tested
(Fisher Transform, Instantaneous Trendline, Voss Predictive Filter,
Trendflex/Reflex, Roofing Filter, MESA MAMA/FAMA, Laguerre RSI, Even Better
Sinewave, Ergodic Oscillator, Adaptive Laguerre Filter) since the Cyber
Cycle's specific 2-pole recursive filter constants (functions of alpha, not
a fixed EMA/SuperSmoother span) and its Cycle-vs-1-bar-lag-Trigger pairing
are a unique construction among them.

Signal logic
------------
- median_price = (high + low) / 2.
- smooth[i] = (median_price[i] + 2*median_price[i-1] + 2*median_price[i-2]
  + median_price[i-3]) / 6.
- cycle[i] = (1 - 0.5*alpha)^2 * (smooth[i] - 2*smooth[i-1] + smooth[i-2])
  + 2*(1-alpha)*cycle[i-1] - (1-alpha)^2*cycle[i-2]  (for i >= warmup bars);
  cycle[i] = (median_price[i] - 2*median_price[i-1] + median_price[i-2]) / 4
  for the first few bars (source's own simplified bootstrap formula).
- trigger[i] = cycle[i-1] (1-bar lag).
- Entry (long): cycle crosses above 0 (zero-line crossover, source's own
  documented uptrend signal).
- Exit: cycle crosses below trigger (Ehlers' own earlier-turning-point
  signal) while cycle is still positive, OR cycle crosses below 0, OR a
  max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series   ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
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


def _compute_cyber_cycle(df: pd.DataFrame, alpha: float) -> pd.Series:
    high, low = df["high"], df["low"]
    median_price = ((high + low) / 2.0).to_numpy(dtype=float)
    n = len(median_price)

    smooth = np.full(n, np.nan)
    for i in range(3, n):
        smooth[i] = (
            median_price[i]
            + 2 * median_price[i - 1]
            + 2 * median_price[i - 2]
            + median_price[i - 3]
        ) / 6.0

    cycle = np.full(n, np.nan)
    coef1 = (1 - 0.5 * alpha) ** 2
    coef2 = 2 * (1 - alpha)
    coef3 = (1 - alpha) ** 2

    for i in range(n):
        if i < 3:
            continue
        if i < 7:
            cycle[i] = (median_price[i] - 2 * median_price[i - 1] + median_price[i - 2]) / 4.0
        else:
            prev1 = cycle[i - 1] if not np.isnan(cycle[i - 1]) else 0.0
            prev2 = cycle[i - 2] if not np.isnan(cycle[i - 2]) else 0.0
            cycle[i] = (
                coef1 * (smooth[i] - 2 * smooth[i - 1] + smooth[i - 2])
                + coef2 * prev1
                - coef3 * prev2
            )

    return pd.Series(cycle, index=df.index)


def generate_signals(
    price_df: pd.DataFrame,
    alpha: float = 0.07,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    cycle = _compute_cyber_cycle(df, alpha)
    trigger = cycle.shift(1)

    cycle_prev = cycle.shift(1)
    zero_cross_up = (cycle > 0) & (cycle_prev <= 0)

    trig_prev = trigger.shift(1)
    cycle_trig_prev = (cycle_prev > trig_prev)
    cross_below_trigger = (cycle <= trigger) & cycle_trig_prev & (cycle > 0)
    zero_cross_down = (cycle < 0) & (cycle_prev >= 0)

    entry = zero_cross_up.fillna(False)
    exit_signal = (cross_below_trigger | zero_cross_down).fillna(False)

    n = len(df)
    entry_arr = entry.to_numpy()
    exit_arr = exit_signal.to_numpy()
    pos_arr = [0] * n

    in_pos = False
    hold_counter = 0
    for i in range(n):
        if in_pos:
            hold_counter += 1
            exit_now = bool(exit_arr[i]) or hold_counter >= max_hold_days
            if exit_now:
                in_pos = False
                hold_counter = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if bool(entry_arr[i]):
                in_pos = True
                hold_counter = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    alpha: float = 0.07,
    max_hold_days: int = 15,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(price_df, alpha=alpha, max_hold_days=max_hold_days)
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
