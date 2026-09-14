"""Strategy: SMA(trend_window) directional gate with continuous ZigZag
"trend maturity" sizing overlay + deadband, leverage-cap-aware for crypto
from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
ZigZag indicator (per Google AI-overview cross-referencing
Investopedia/LuxAlgo/NAGA/Angel One, browser_exec fallback since web_search
DDG backend failed for this query): a repainting-safe percent-deviation
construction that only confirms a new swing pivot once price reverses from
the last extreme by a threshold percentage:
    pct_change = (current_price - prev_swing_price) / prev_swing_price * 100
This repo has 6 prior ZigZag entries (2026-09-05-089, 2026-09-07-028,
2026-09-08-050/091/107, 2026-09-12-200), ALL binary breakout/pattern
triggers off confirmed pivots (mostly rejected, one QQQ-only accept). None
used the ZigZag's underlying continuous % move-since-last-confirmed-pivot
as a SIZING dial. This iteration reframes it as "trend maturity": the
signed % distance of current close from the last CONFIRMED swing pivot
(itself confirmed only after a `zigzag_deviation_pct` reversal, so no
lookahead off the still-forming leg), rolling z-scored + tanh-squashed to
[-1,+1], used as a sizing multiplier within an SMA(trend_window) uptrend
gate. Economic rationale: a larger confirmed move since the last swing low
signals the current up-leg has more momentum/conviction, warranting larger
exposure, vs. a close still hugging its last confirmed pivot (low
conviction, near-decision-point). First ZigZag continuous-sizing variant.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
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


def _confirmed_zigzag_pct_from_last_pivot(
    close: pd.Series, deviation_pct: float
) -> pd.Series:
    """At each bar, return the signed % distance of `close` from the most
    recently CONFIRMED zigzag pivot (confirmed strictly using data up to
    and including the current bar -- a pivot only becomes "confirmed" once
    price has reversed from the running extreme by >= deviation_pct, which
    by construction only uses past+current data, no lookahead).
    """
    n = len(close)
    vals = close.to_numpy()
    out = np.zeros(n)

    if n == 0:
        return pd.Series(out, index=close.index)

    last_confirmed_pivot = vals[0]
    # running extreme since the last confirmed pivot
    running_extreme = vals[0]
    direction = 0  # 0 = undetermined (first leg not yet confirmed either way),
                   # 1 = tracking a potential swing HIGH (extreme is a max),
                   # -1 = tracking a potential swing LOW (extreme is a min)

    for i in range(n):
        price = vals[i]

        if direction == 0:
            # Undetermined: track both a running max and min from the start
            # via a single extreme that we test in both directions; the
            # first threshold breach (up or down) fixes the initial leg.
            if price > running_extreme:
                running_extreme = price
            elif price < running_extreme:
                running_extreme = price
            # test breach in either direction from the ORIGINAL starting
            # price (vals[0]) since no leg is established yet
            rally = (running_extreme - vals[0]) / vals[0] * 100.0 if vals[0] != 0 else 0.0
            drawdown = (vals[0] - running_extreme) / vals[0] * 100.0 if vals[0] != 0 else 0.0
            if rally >= deviation_pct:
                last_confirmed_pivot = vals[0]
                direction = 1  # now tracking a swing high (up leg)
                running_extreme = price
            elif drawdown >= deviation_pct:
                last_confirmed_pivot = vals[0]
                direction = -1  # now tracking a swing low (down leg)
                running_extreme = price
        elif direction == 1:
            if price > running_extreme:
                running_extreme = price
            pullback = (running_extreme - price) / running_extreme * 100.0 if running_extreme != 0 else 0.0
            if pullback >= deviation_pct:
                last_confirmed_pivot = running_extreme
                direction = -1
                running_extreme = price
        else:  # direction == -1
            if price < running_extreme:
                running_extreme = price
            bounce = (price - running_extreme) / running_extreme * 100.0 if running_extreme != 0 else 0.0
            if bounce >= deviation_pct:
                last_confirmed_pivot = running_extreme
                direction = 1
                running_extreme = price

        out[i] = (price - last_confirmed_pivot) / last_confirmed_pivot * 100.0 if last_confirmed_pivot != 0 else 0.0

    return pd.Series(out, index=close.index)


def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
    raw = raw_exposure.fillna(0.0).to_numpy()
    held = np.zeros_like(raw)
    current = 0.0
    for i, r in enumerate(raw):
        if abs(r - current) > deadband:
            current = r
        held[i] = current
    return pd.Series(held, index=raw_exposure.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    zigzag_deviation_pct: float = 5.0,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Signed % distance of close from the last CONFIRMED zigzag pivot ("trend
    maturity") is rolling-z-scored over `zscore_window` bars and
    tanh-squashed to [-1,+1] before use as a sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    pct_from_pivot = _confirmed_zigzag_pct_from_last_pivot(close, zigzag_deviation_pct)

    roll_mean = pct_from_pivot.rolling(zscore_window).mean()
    roll_std = pct_from_pivot.rolling(zscore_window).std()
    zscore = (pct_from_pivot - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    zigzag_deviation_pct: float = 5.0,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        zigzag_deviation_pct=zigzag_deviation_pct,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
