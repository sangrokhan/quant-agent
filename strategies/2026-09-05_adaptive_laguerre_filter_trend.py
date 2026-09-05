"""Strategy: Adaptive Laguerre Filter (ALF) slope + price-position trend
following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-058):
Per quantifiedstrategies.com's "Adaptive Laguerre Filter" article, the ALF
(John Ehlers) is a triangular-weighted-average-like smoother of price with
an ADAPTIVE gamma feedback factor that varies based on how well the filter
has been tracking recent price -- it hugs price closely in trends and goes
flat/slow in consolidation, reducing whipsaws relative to a fixed-gamma
smoother. The article's disclosed (non-paywalled) interpretation rule: when
the filter is SLOPING UP and price is trading ABOVE it, the market is
trending up and likely to continue; when sloping down with price below, a
downtrend. This is implemented here as a mechanical long/flat rule: long
when ALF's `slope_lookback`-bar slope is positive AND close is above ALF;
exit when either condition breaks, or a max_hold_days time-stop.

This is a genuinely different construction from the previously-tested
Laguerre RSI (2026-09-05-053, rejected): that strategy used Ehlers'
4-stage Laguerre filter cascade to build an RSI-style BOUNDED OSCILLATOR
(0 to 1) with fixed gamma, mean-reversion oscillator-threshold entries. The
Adaptive Laguerre Filter here is instead a PRICE-DOMAIN smoothing line
(same units as price, not bounded 0-1) with an ADAPTIVE (not fixed) gamma,
used as a trend-following overlay (slope + price-position), not a
mean-reversion oscillator.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _adaptive_laguerre_filter(price: pd.Series, lookback: int) -> pd.Series:
    """Ehlers' Adaptive Laguerre Filter.

    gamma is adapted each bar based on the tracking error over the
    trailing `lookback` window (Ehlers' original design compares current
    filter output to price highs/lows over the lookback; we use a
    simplified but faithful proxy: gamma scales with normalized recent
    price range vs. the filter's own recent range, clipped to [0.05, 0.95]).
    """
    n = len(price)
    values = price.values.astype(float)
    L0 = L1 = L2 = L3 = 0.0
    out = [0.0] * n
    roll_high = price.rolling(lookback).max().values
    roll_low = price.rolling(lookback).min().values

    for i in range(n):
        rng = roll_high[i] - roll_low[i] if i >= lookback - 1 else None
        if rng is not None and rng > 0:
            # Normalized distance of current price from the midpoint of its
            # recent range -> higher when trending/near an extreme (fast),
            # lower when centered (slow) -- an Ehlers-style adaptive proxy.
            mid = (roll_high[i] + roll_low[i]) / 2.0
            gamma = min(0.95, max(0.05, abs(values[i] - mid) / (rng / 2.0)))
        else:
            gamma = 0.5

        L0_prev, L1_prev, L2_prev, L3_prev = L0, L1, L2, L3
        L0 = (1 - gamma) * values[i] + gamma * L0_prev
        L1 = -gamma * L0 + L0_prev + gamma * L1_prev
        L2 = -gamma * L1 + L1_prev + gamma * L2_prev
        L3 = -gamma * L2 + L2_prev + gamma * L3_prev
        out[i] = (L0 + 2 * L1 + 2 * L2 + L3) / 6.0

    return pd.Series(out, index=price.index)


def generate_signals(
    price_df: pd.DataFrame,
    alf_lookback: int = 20,
    slope_lookback: int = 5,
    max_hold_days: int = 25,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry (long): ALF's slope over `slope_lookback` bars is positive AND
    close is above the ALF line.
    Exit: either condition breaks, or a max_hold_days time-stop.
    """
    df = _prep(price_df)
    close = df["close"]

    alf = _adaptive_laguerre_filter(close, alf_lookback)
    slope = alf - alf.shift(slope_lookback)

    trend_up = (slope > 0) & (close > alf)

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(n):
        cond = bool(trend_up.iloc[i]) if not pd.isna(trend_up.iloc[i]) else False
        if in_position:
            held = i - entry_idx
            if (not cond) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if cond:
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
