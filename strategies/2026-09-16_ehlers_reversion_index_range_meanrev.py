"""Strategy: John F. Ehlers' Reversion Index (TASC Jan 2026, "Identifying
Peaks And Valleys In Ranging Markets") mean-reversion long entry on
Trigger/Smooth crossover at a valley.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
Per PineCodersTASC's exact disclosed Pine v6 source
(https://www.tradingview.com/script/V35NeC45-TASC-2026-01-The-Reversion-Index/,
visited this iteration via browser_exec since this exact URL wasn't yet in
the ledger -- web_search returned no results for the discovery query, fell
back to browser_exec Google SERP per RESEARCH_LOOP.md): the raw Reversion
Index (RI) is the net change in price over a rolling `length`-bar window,
normalized by the sum of absolute changes over that same window:
    RI = sum(close - close.shift(1), length) / sum(|close - close.shift(1)|, length)
naturally bounded in [-1, +1] (all up days -> +1, all down days -> -1,
choppy/ranging -> near 0). Ehlers then applies his 2-pole SuperSmoother
filter (low-lag Butterworth-style smoother) to RI at two different periods:
`Smooth` = SuperSmoother(RI, 8), `Trigger` = SuperSmoother(RI, 4) (half the
Smooth period, so it leads). Ehlers' own disclosed usage rule: peaks and
valleys in ranging/cyclical price action are identified by the Trigger line
crossing the Smooth line -- Trigger crossing above Smooth marks a valley
(price bottom, buy), Trigger crossing below Smooth marks a peak (price top,
sell/exit). Ehlers explicitly designed this for ranging markets (not
trending), and suggests `length` be set to roughly half the expected cycle
length of the data.

First Ehlers Reversion Index / net-change-ratio-normalized-then-SuperSmoothed
oscillator in this repo -- distinct from this repo's other Ehlers-family
entries (Cyber Cycle, Adaptive Cyber Cycle, Roofing Filter/Decycler,
Instantaneous Trendline, MESA) which all use bandpass/highpass/adaptive-cycle
filter constructions on raw price, not a normalized net-change ratio.
Because Ehlers frames this as a ranging-market mean-reversion tool, this
strategy is long-only and entered without an uptrend gate (the crossover
signal itself is the mean-reversion trigger, per source), with a time-stop
backstop and an optional light trend/volatility qualifier (skip entries
already deep in a strong established trend, since RI is designed for
choppy/ranging conditions, not trending ones) -- implemented here as an ADX-
free simple check: only trade when price is within `range_band_pct` of its
own rolling `range_window`-bar midpoint (a cheap "is this a range, not a
trend" proxy using only OHLCV, no additional external indicator needed).

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position series)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _reversion_index(close: pd.Series, length: int) -> pd.Series:
    d = close.diff()
    ds = d.rolling(length).sum()
    ads = d.abs().rolling(length).sum()
    ri = ds / ads.replace(0.0, np.nan)
    return ri.fillna(0.0)


def _super_smoother(series: pd.Series, period: int) -> pd.Series:
    """Ehlers' 2-pole SuperSmoother filter (low-lag Butterworth-style)."""
    alpha = math.pi * math.sqrt(2.0) / period
    beta = math.exp(-alpha)
    coef2 = -(beta ** 2)
    coef1 = math.cos(alpha) * 2.0 * beta
    coef0 = 1.0 - coef1 - coef2

    vals = series.fillna(0.0).to_numpy()
    n = len(vals)
    smooth = np.zeros(n)
    for i in range(n):
        s_prev1 = smooth[i - 1] if i >= 1 else 0.0
        s_prev2 = smooth[i - 2] if i >= 2 else 0.0
        v_prev1 = vals[i - 1] if i >= 1 else vals[i]
        sma2 = 0.5 * (vals[i] + v_prev1)
        smooth[i] = coef0 * sma2 + coef1 * s_prev1 + coef2 * s_prev2
    return pd.Series(smooth, index=series.index)


def _range_regime_ok(close: pd.Series, range_window: int, range_band_pct: float) -> pd.Series:
    """Cheap proxy for 'ranging, not strongly trending' using only close
    prices: True when close is within `range_band_pct` of its own rolling
    midpoint over `range_window` bars (i.e. hasn't broken decisively out).
    """
    roll_high = close.rolling(range_window).max()
    roll_low = close.rolling(range_window).min()
    midpoint = (roll_high + roll_low) / 2.0
    band = (roll_high - roll_low) / 2.0 * (1.0 + range_band_pct)
    ok = (close - midpoint).abs() <= band
    return ok.fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    ri_length: int = 20,
    smooth_period: int = 8,
    trigger_period: int = 4,
    range_window: int = 60,
    range_band_pct: float = 0.5,
    max_hold_days: int = 15,
) -> pd.Series:
    """0/1 long-only position series.

    Entry: Trigger (fast SuperSmoother of RI) crosses above Smooth (slow
    SuperSmoother of RI) -- a valley signal per Ehlers' own disclosed rule --
    while price is in a "ranging" regime (cheap proxy: within range_band_pct
    of its rolling range_window-bar midpoint, since Ehlers explicitly says
    this indicator is for ranging, not trending, markets).
    Exit: Trigger crosses back below Smooth (a peak signal), or
    max_hold_days bars have elapsed since entry, whichever comes first.
    """
    df = _prep(price_df)
    close = df["close"]

    ri = _reversion_index(close, ri_length)
    smooth = _super_smoother(ri, smooth_period)
    trigger = _super_smoother(ri, trigger_period)

    range_ok = _range_regime_ok(close, range_window, range_band_pct)

    cross_up = (trigger > smooth) & (trigger.shift(1) <= smooth.shift(1))
    cross_down = (trigger < smooth) & (trigger.shift(1) >= smooth.shift(1))

    entry_trigger = (cross_up & range_ok).fillna(False).to_numpy()
    exit_trigger = cross_down.fillna(False).to_numpy()

    n = len(close)
    position = np.zeros(n)
    in_pos = False
    bars_held = 0
    for i in range(n):
        if in_pos:
            bars_held += 1
            if exit_trigger[i] or bars_held >= max_hold_days:
                in_pos = False
                bars_held = 0
            else:
                position[i] = 1.0
        else:
            if entry_trigger[i]:
                in_pos = True
                bars_held = 0
                position[i] = 1.0

    return pd.Series(position, index=close.index)


def generate_returns(
    price_df: pd.DataFrame,
    ri_length: int = 20,
    smooth_period: int = 8,
    trigger_period: int = 4,
    range_window: int = 60,
    range_band_pct: float = 0.5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        ri_length=ri_length,
        smooth_period=smooth_period,
        trigger_period=trigger_period,
        range_window=range_window,
        range_band_pct=range_band_pct,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret
