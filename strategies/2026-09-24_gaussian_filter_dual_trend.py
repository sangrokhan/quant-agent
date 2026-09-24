"""Strategy: Dual-Gaussian-Filter trend following with distance-threshold entry gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-064):
A multi-pole Gaussian-weighted moving average (cascading N-pole convolution
with a Gaussian kernel) provides an optimally-smoothed trend reference line
with less lag-for-a-given-smoothness tradeoff than a plain SMA/EMA of the
same lookback. Per RunBacktest's Gaussian Filter strategy documentation
(https://runbacktest.com/trading-strategies/gaussian-filter, read this
iteration via browser_exec -- web_search DDGS erroring on this iteration's
initial "Standard Deviation Channel breakout" query, so the fallback browser
search led to RunBacktest's strategy library and this indicator, which had
0 prior KB hits): a dual-filter design (fast Gaussian crossing above a
slower Gaussian = trend-up regime) combined with a "price must stay within
distanceThresholdPercent of the (slow) Gaussian line" entry gate should
avoid chasing extended/overbought breakouts while still catching sustained
trends -- distinct from every existing MA-crossover strategy in this repo
because the Gaussian kernel weighting (bell-curve, cascaded through
`poles` passes) produces markedly different (less overshoot, tighter
lag-vs-noise tradeoff) smoothing characteristics than SMA/EMA/WMA already
tested here, and the distance-threshold gate is a novel entry-filter shape
not previously used in this repo's crossover-family strategies.

Signal logic
------------
- Gaussian(period, poles): approximate a poles-pole cascaded Gaussian filter
  by applying an EMA repeatedly `poles` times with a per-pole smoothing
  alpha, where alpha is derived from `period` (a standard technique used to
  approximate a true N-pole Gaussian/Butterworth-style filter with a small,
  fast pandas-native ewm chain -- this is NOT reimplementing backtest
  execution mechanics, it's the trading-logic signal itself).
- Fast Gaussian = Gaussian(fastPeriod, poles); Slow Gaussian =
  Gaussian(slowPeriod, poles).
- Entry (long): fast Gaussian crosses above slow Gaussian (trend-up regime
  begins) AND close is within distanceThresholdPercent of the slow Gaussian
  line (not already extended away from the trend baseline).
- Exit: fast Gaussian crosses back below slow Gaussian, OR close diverges
  more than 3x distanceThresholdPercent from the slow Gaussian line
  (extended-breakout risk-off exit), OR a max holding period of
  max_hold_days trading days.
- Flat (no position) otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _gaussian_filter(series: pd.Series, period: int, poles: int) -> pd.Series:
    """Approximate a `poles`-pole cascaded Gaussian filter via repeated EMA passes.

    A true N-pole Gaussian filter cascades N single-pole low-pass stages;
    approximating each stage with an EMA of the same effective smoothing
    period (alpha derived from `period`) reproduces the qualitative
    behaviour (progressively smoother, slightly more lag per added pole)
    without needing a full FIR/IIR convolution implementation.
    """
    alpha = 2.0 / (period + 1.0)
    out = series.copy()
    for _ in range(max(1, poles)):
        out = out.ewm(alpha=alpha, adjust=False, min_periods=period).mean()
    return out


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 20,
    poles: int = 4,
    fast_period: int = 10,
    slow_period: int = 30,
    distance_threshold_pct: float = 0.5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fast_g = _gaussian_filter(close, fast_period, poles)
    slow_g = _gaussian_filter(close, slow_period, poles)

    entry_gate = (close - slow_g).abs() / slow_g <= (distance_threshold_pct / 100.0)
    exit_gate = (close - slow_g).abs() / slow_g > (3.0 * distance_threshold_pct / 100.0)

    trend_up = fast_g > slow_g
    trend_up_prev = trend_up.shift(1).fillna(False)
    cross_up = trend_up & (~trend_up_prev)
    cross_down = (~trend_up) & trend_up_prev

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    hold_days = 0

    idx = close.index
    for i in range(len(idx)):
        if not in_position:
            if bool(cross_up.iloc[i]) and bool(entry_gate.iloc[i]):
                in_position = True
                hold_days = 0
        else:
            hold_days += 1
            should_exit = bool(cross_down.iloc[i]) or bool(exit_gate.iloc[i]) or (hold_days >= max_hold_days)
            if should_exit:
                in_position = False
        position.iloc[i] = 1 if in_position else 0

    position = position.fillna(0).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    period: int = 20,
    poles: int = 4,
    fast_period: int = 10,
    slow_period: int = 30,
    distance_threshold_pct: float = 0.5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        period=period,
        poles=poles,
        fast_period=fast_period,
        slow_period=slow_period,
        distance_threshold_pct=distance_threshold_pct,
        max_hold_days=max_hold_days,
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
