"""Strategy: Ehlers CyberCycle vs Trigger-line crossover trend/cycle following.

Source: John F. Ehlers' CyberCycle indicator (originally published in
"Rocket Science for Traders", widely reproduced verbatim across DSP-trading
sites; formula confirmed via Bing SERP featured snippet this iteration --
web_search DDGS backend failed with a TLS RequestError on the first query
attempted, so the browser_exec Bing fallback was used for the whole
iteration):

    alpha = 2 / (Length + 1)
    Smooth_t = (Price_t + 2*Price_{t-1} + 2*Price_{t-2} + Price_{t-3}) / 6
    Cycle_t = (1 - 0.5*alpha)^2 * (Smooth_t - 2*Smooth_{t-1} + Smooth_{t-2})
              + 2*(1 - alpha)*Cycle_{t-1} - (1 - alpha)^2 * Cycle_{t-2}
    Trigger_t = Cycle_{t-1}   (Ehlers' own 1-bar-lagged "signal line")

This is architecturally distinct from every other Ehlers-family strategy
already in this repo (2026-09-13-024/025 PMA slope-turn uses a linear-
regression forward-projection with NO recursive high-pass/low-pass
filtering; the SuperSmoother-based Poor Man's Trend uses a pure 2-pole
IIR low-pass with zero band-pass/cycle-extraction behavior). CyberCycle is
instead a 2nd-order high-pass filter cascaded onto a 4-bar FIR smoother,
specifically designed by Ehlers to isolate short-term price CYCLES
(bandpass-like behavior) rather than trend, and its own textbook trading
rule is a Cycle/Trigger crossover (analogous to a fast/slow oscillator
cross), not a trend-turn or slope-turn rule. 0 prior "CyberCycle" hits in
this repo's knowledge_base index (distinct from the unrelated "Ehlers
Roofing" and "Ehlers PMA" entries).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's
id): Ehlers designed CyberCycle's cascaded high-pass + FIR-smoother
construction specifically to strip out both high-frequency noise and
low-frequency trend, leaving the market's dominant short cycle. Going long
when the fast Cycle line crosses above its own 1-bar-lagged Trigger line
(and flat/short on the mirror cross) should catch cycle-driven swings that
pure trend-following (SMA/EMA crossover) or slope-projection (PMA) methods
in this repo miss, at least in choppy/non-trending regimes -- with a
longer-term SMA trend filter added (following this repo's established
"unfiltered Ehlers oscillators tend to whipsaw" pattern from the PMA
near-miss) and a max_hold_days time-stop to bound rare hangover trades.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} long/flat position series aligned to price_df.index.
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


def _compute_cybercycle(close: pd.Series, length: int) -> pd.Series:
    """Ehlers CyberCycle recursive filter (see module docstring for formula)."""
    n = len(close)
    price = close.values
    alpha = 2.0 / (length + 1.0)

    smooth = np.zeros(n)
    cycle = np.zeros(n)

    for i in range(n):
        if i < 3:
            smooth[i] = price[i]
            cycle[i] = 0.0
            continue
        smooth[i] = (price[i] + 2 * price[i - 1] + 2 * price[i - 2] + price[i - 3]) / 6.0
        if i < 6:
            # Ehlers' own initialization: use a simple 2nd-difference of price
            # for the first few bars where the recursive terms aren't warmed up.
            cycle[i] = (price[i] - 2 * price[i - 1] + price[i - 2]) / 4.0
        else:
            cycle[i] = (
                (1 - 0.5 * alpha) ** 2 * (smooth[i] - 2 * smooth[i - 1] + smooth[i - 2])
                + 2 * (1 - alpha) * cycle[i - 1]
                - (1 - alpha) ** 2 * cycle[i - 2]
            )

    return pd.Series(cycle, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    length: int = 10,
    trend_window: int = 100,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    cycle = _compute_cybercycle(close, length)
    trigger = cycle.shift(1)

    trend_sma = close.rolling(trend_window).mean()
    uptrend = (close > trend_sma).fillna(False)

    cross_up = (cycle > trigger) & (cycle.shift(1) <= trigger.shift(1))
    cross_down = (cycle < trigger) & (cycle.shift(1) >= trigger.shift(1))
    cross_up = cross_up.fillna(False)
    cross_down = cross_down.fillna(False)

    entry_cond = (cross_up & uptrend).fillna(False)
    exit_cond = (cross_down | (~uptrend)).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cond.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_cond.iloc[i]):
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
