"""Strategy: Stacked-MA progressive de-risking exposure (8 EMA / 21 EMA /
50 SMA / 200 SMA structure-breakdown staged exit), long-only continuous
exposure dial.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-018):
Per TOSIndicators.com's "How to Recognize When a Trend Reverses"
(https://tosindicators.com/research/trend-reverses, visited this
iteration), a healthy uptrend has 8 EMA > 21 EMA > 50 SMA > 200 SMA (fully
stacked bullish). As a trend deteriorates, this structure breaks down in a
specific SEQUENCE, and the source's own disclosed table maps each stage to
a suggested action:

    Fully Stacked Bullish (8>21>50>200)  -> Hold longs, trail stops
    Price Below 8 EMA                    -> Tighten stops
    8 EMA Below 21 EMA                   -> Exit partial position
    50 SMA Rolling Over (sloping down)   -> Exit remaining longs
    Fully Stacked Bearish (8<21<50<200)  -> Short or cash

This is distinct from every other MA-ribbon strategy already in this repo
(2026-09-04-068/070's TEMA/Triple-EMA dual crossovers are single binary
entry/exit triggers; 2026-09-21-179's 5/8/13/21 EMA ribbon is a single
binary full-stack-or-not filter): this source's own framework is a
PROGRESSIVE, multi-stage de-risking EXIT mechanism tied to the ORDER in
which structure breaks down, not a single crossover. Modeled here as a
continuous long-only exposure dial (matching this repo's existing
continuous-sizing-dial convention) rather than forcing it into a binary
0/1 position, since "exit partial" doesn't map cleanly to a binary signal:

    Stage 0 (fully stacked bullish, price>=8EMA): exposure = 1.0
    Stage 1 (price<8EMA but 8EMA>=21EMA):         exposure = 0.66
    Stage 2 (8EMA<21EMA but 50SMA not rolling
             over, i.e. 50SMA slope>=0):           exposure = 0.33
    Stage 3 (50SMA rolling over, i.e. 50SMA
             slope<0) or fully stacked bearish:     exposure = 0.0

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (here: continuous
        exposure in [0, 1], not strictly {0,1} -- validators/grid_test
        operate on generate_returns directly so this is compatible)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    fast_ema: int = 5,
    mid_ema: int = 26,
    slow_sma: int = 40,
    macro_sma: int = 200,
    rollover_slope_window: int = 5,
    stage1_exposure: float = 0.75,
    stage2_exposure: float = 0.2,
) -> pd.Series:
    """Return a continuous [0,1] exposure series (long-only)."""
    df = _prep(price_df)
    close = df["close"]

    ema_fast = close.ewm(span=fast_ema, adjust=False).mean()
    ema_mid = close.ewm(span=mid_ema, adjust=False).mean()
    sma_slow = close.rolling(slow_sma).mean()
    sma_macro = close.rolling(macro_sma).mean()

    sma_slow_slope = sma_slow.diff(rollover_slope_window)
    rolling_over = sma_slow_slope < 0.0

    fully_bullish = (ema_fast > ema_mid) & (ema_mid > sma_slow) & (sma_slow > sma_macro)
    price_below_fast = close < ema_fast
    fast_below_mid = ema_fast < ema_mid
    fully_bearish = (ema_fast < ema_mid) & (ema_mid < sma_slow) & (sma_slow < sma_macro)

    exposure = pd.Series(0.0, index=close.index)

    stage0_mask = fully_bullish & ~price_below_fast
    stage1_mask = ~stage0_mask & price_below_fast & ~fast_below_mid & ~fully_bearish
    stage2_mask = ~stage0_mask & ~stage1_mask & fast_below_mid & ~rolling_over & ~fully_bearish
    # everything else (stage3): rolling_over or fully_bearish -> exposure stays 0.0

    exposure[stage0_mask] = 1.0
    exposure[stage1_mask] = stage1_exposure
    exposure[stage2_mask] = stage2_exposure

    return exposure.fillna(0.0)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Exposure-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
