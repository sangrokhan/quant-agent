"""Strategy: Ehlers Recursive Median Oscillator (RMO) zero-cross (TASC Mar 2018).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-148):
John Ehlers' TASC Mar 2018 article "Recursive Median Filters" introduces a
two-stage filter: (1) a 5-bar rolling MEDIAN (robust to outlier spikes,
unlike a mean-based average) smoothed by a single-pole EMA whose alpha is
derived from a cosine/sine cycle-period formula (LPPeriod=12 default);
(2) that recursive median is then passed through a 2-pole highpass filter
(HPPeriod=30 default) to strip out slow trend components, leaving a
near-zero-lag oscillator (RMO) that fluctuates around zero. Ehlers' own
comparison: "by being able to smooth the data with the least amount of lag,
the recursive median oscillator may give the trader a better view of the
bigger picture" versus the classic RSI.

This is a genuinely novel Ehlers construction for this repo (distinct from
all prior Ehlers entries -- Fisher Transform, MESA Stochastic, Center-of-
Gravity, Instantaneous Trendline, Decycler, Laguerre RSI/ALF, Roofing
Filter, MAMA/FAMA, Trendflex/Reflex, Inverse Fisher Transform, MESA Sine
Wave -- NONE use a median-filter base rather than an EMA/SuperSmoother
base as the first-stage smoother).

Source discloses only the raw indicator (no explicit trading rule); our
own addition (flagged as such): long entry when RMO crosses above zero
(oscillator turning positive, i.e. the median-filtered price is
accelerating relative to its own recent highpass-filtered trend), exit on
the reverse zero-cross or a max_hold_days time-stop.

Source: https://traders.com/Documentation/FEEDbk_docs/2018/03/TradersTips.html
(TradeStation section, read via browser_exec).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _recursive_median_oscillator(close: pd.Series, lp_period: int, hp_period: int) -> pd.Series:
    n = len(close)
    vals = close.to_numpy(dtype=float)

    # Alpha1: EMA smoothing constant for the recursive median filter.
    rad1 = math.radians(360.0 / lp_period)
    alpha1 = (math.cos(rad1) + math.sin(rad1) - 1) / math.cos(rad1)

    # Alpha2: highpass filter constant.
    rad2 = math.radians(0.707 * 360.0 / hp_period)
    alpha2 = (math.cos(rad2) + math.sin(rad2) - 1) / math.cos(rad2)

    median5 = close.rolling(5).median().to_numpy(dtype=float)

    rm = [0.0] * n
    rmo = [0.0] * n
    for i in range(n):
        med = median5[i] if not math.isnan(median5[i]) else vals[i]
        prev_rm = rm[i - 1] if i > 0 else 0.0
        rm[i] = alpha1 * med + (1 - alpha1) * prev_rm

        rm_1 = rm[i - 1] if i > 0 else 0.0
        rm_2 = rm[i - 2] if i > 1 else 0.0
        rmo_1 = rmo[i - 1] if i > 0 else 0.0
        rmo_2 = rmo[i - 2] if i > 1 else 0.0

        term1 = (1 - alpha2 / 2) ** 2 * (rm[i] - 2 * rm_1 + rm_2)
        term2 = 2 * (1 - alpha2) * rmo_1
        term3 = (1 - alpha2) ** 2 * rmo_2
        rmo[i] = term1 + term2 - term3

    return pd.Series(rmo, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    lp_period: int = 12,
    hp_period: int = 30,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rmo = _recursive_median_oscillator(close, lp_period, hp_period)

    entry = (rmo > 0) & (rmo.shift(1) <= 0)
    exit_cross = (rmo < 0) & (rmo.shift(1) >= 0)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or held >= max_hold_days:
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
