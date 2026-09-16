"""Strategy: MAMA-FAMA spread as a continuous exposure-sizing dial (SMA
trend gate), leverage-cap-aware for crypto.

Hypothesis (this cron trigger's own research): distinct TECHNIQUE from
this trigger's own MAMA/FAMA binary crossover variants (2026-09-06-101,
2026-09-17-091/092/093) -- rather than a discrete long/flat crossover
signal, this strategy uses the normalized MAMA-FAMA SPREAD itself as a
continuous position-sizing dial (this repo's established "continuous
sizing dial" pattern, e.g. 2026-09-14-177 PVO, 2026-09-14-121 Elder-Ray),
inside an SMA(trend_window) uptrend gate. The intuition: the raw spread
magnitude (not just its sign) should carry information about trend
CONVICTION -- per iwpfinance.com's own account (confirmed this iteration),
"a visible gap opens between MAMA above and FAMA below, confirming the up
phase" during a strong breakout, while during a range the two lines
"hug each other near mid-range price" -- so exposure should scale with
gap width, going flat/near-flat during choppy near-touches (exactly the
whipsaw failure mode the binary crossover variants had to fix with
min_hold_days/parameter retuning) rather than the binary approach of
having to filter whipsaw ex-post.

Formula: uses the identical Hilbert-transform MAMA/FAMA recursion as
strategies/2026-09-06_mama_fama_crossover.py and
strategies/2026-09-17_mama_fama_min_hold_fix.py (same source:
https://www.luxalgo.com/library/indicator/mama-fama/, formula behavior
re-confirmed via https://iwpfinance.com/concepts/technical-analysis/mama-fama-mesa-adaptive
this cron trigger).

Signal logic
------------
- spread = (MAMA - FAMA) / close (normalized by price level)
- rolling z-score of spread over norm_window, tanh-squashed to [-1, 1]
- exposure = clip(base_exposure + sensitivity * dial, 0, leverage_cap),
  gated to zero whenever close < SMA(trend_window) (only take long
  exposure in a confirmed uptrend) and whenever |dial| < deadband (avoid
  churning on noise near zero).

Interface contract: both generate_signals and generate_returns accept all
tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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


def _mama_fama(
    price: pd.Series, fast_limit: float, slow_limit: float
) -> tuple[pd.Series, pd.Series]:
    """Ehlers' MESA Adaptive Moving Average (identical implementation to
    strategies/2026-09-06_mama_fama_crossover.py).
    """
    p = price.to_numpy(dtype=float)
    n = len(p)

    smooth = np.zeros(n)
    detrender = np.zeros(n)
    i1 = np.zeros(n)
    q1 = np.zeros(n)
    ji = np.zeros(n)
    jq = np.zeros(n)
    i2 = np.zeros(n)
    q2 = np.zeros(n)
    re = np.zeros(n)
    im = np.zeros(n)
    period = np.zeros(n)
    smooth_period = np.zeros(n)
    phase = np.zeros(n)
    mama = np.zeros(n)
    fama = np.zeros(n)

    for t in range(n):
        if t < 6:
            mama[t] = p[t]
            fama[t] = p[t]
            period[t] = 0.0
            continue

        smooth[t] = (4 * p[t] + 3 * p[t - 1] + 2 * p[t - 2] + p[t - 3]) / 10.0
        prev_period = period[t - 1] if period[t - 1] else 15.0
        adj = 0.075 * prev_period + 0.54

        detrender[t] = (
            0.0962 * smooth[t]
            + 0.5769 * smooth[t - 2]
            - 0.5769 * smooth[t - 4]
            - 0.0962 * smooth[t - 6]
        ) * adj

        q1[t] = (
            0.0962 * detrender[t]
            + 0.5769 * detrender[t - 2]
            - 0.5769 * detrender[t - 4]
            - 0.0962 * detrender[t - 6]
        ) * adj
        i1[t] = detrender[t - 3]

        ji[t] = (
            0.0962 * i1[t] + 0.5769 * i1[t - 2] - 0.5769 * i1[t - 4] - 0.0962 * i1[t - 6]
        ) * adj
        jq[t] = (
            0.0962 * q1[t] + 0.5769 * q1[t - 2] - 0.5769 * q1[t - 4] - 0.0962 * q1[t - 6]
        ) * adj

        i2_raw = i1[t] - jq[t]
        q2_raw = q1[t] + ji[t]
        i2[t] = 0.2 * i2_raw + 0.8 * i2[t - 1]
        q2[t] = 0.2 * q2_raw + 0.8 * q2[t - 1]

        re_raw = i2[t] * i2[t - 1] + q2[t] * q2[t - 1]
        im_raw = i2[t] * q2[t - 1] - q2[t] * i2[t - 1]
        re[t] = 0.2 * re_raw + 0.8 * re[t - 1]
        im[t] = 0.2 * im_raw + 0.8 * im[t - 1]

        if re[t] != 0 and im[t] != 0:
            cur_period = 360.0 / (np.degrees(np.arctan(im[t] / re[t])) if re[t] != 0 else 0.0001)
        else:
            cur_period = period[t - 1]
        if not np.isfinite(cur_period):
            cur_period = period[t - 1]

        if cur_period > 1.5 * period[t - 1]:
            cur_period = 1.5 * period[t - 1]
        if cur_period < 0.67 * period[t - 1]:
            cur_period = 0.67 * period[t - 1]
        if cur_period < 6:
            cur_period = 6
        if cur_period > 50:
            cur_period = 50
        period[t] = 0.2 * cur_period + 0.8 * period[t - 1]
        smooth_period[t] = 0.33 * period[t] + 0.67 * smooth_period[t - 1]

        if i1[t] != 0:
            cur_phase = np.degrees(np.arctan(q1[t] / i1[t]))
        else:
            cur_phase = phase[t - 1]
        phase[t] = cur_phase

        delta_phase = phase[t - 1] - phase[t]
        if delta_phase < 1:
            delta_phase = 1

        alpha = fast_limit / delta_phase
        if alpha < slow_limit:
            alpha = slow_limit
        if alpha > fast_limit:
            alpha = fast_limit

        mama[t] = alpha * p[t] + (1 - alpha) * mama[t - 1]
        fama[t] = 0.5 * alpha * mama[t] + (1 - 0.5 * alpha) * fama[t - 1]

    return pd.Series(mama, index=price.index), pd.Series(fama, index=price.index)


def generate_signals(
    price_df: pd.DataFrame,
    fast_limit: float = 0.5,
    slow_limit: float = 0.05,
    trend_window: int = 40,
    norm_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    deadband: float = 0.15,
    leverage_cap: float = 1.0,
    rebalance_step: float = 0.25,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]
    hl2 = (df["high"] + df["low"]) / 2.0

    mama, fama = _mama_fama(hl2, fast_limit, slow_limit)
    spread = (mama - fama) / close

    rolling_mean = spread.rolling(norm_window).mean()
    rolling_std = spread.rolling(norm_window).std()
    zscore = (spread - rolling_mean) / rolling_std.replace(0.0, np.nan)
    dial = np.tanh(zscore).fillna(0.0)

    trend_gate = close > close.rolling(trend_window).mean()

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.where(dial.abs() >= deadband, 0.0)
    raw_exposure = raw_exposure.where(trend_gate, 0.0)
    exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    # Quantize to a coarse grid (rebalance_step) to cut daily-rebalancing
    # trade count -- continuous dials that re-trade every single day the
    # underlying spread wiggles fail transaction-cost-survival decisively
    # (this repo's established issue with unthrottled sizing dials);
    # rounding to a coarse step means exposure only actually changes (and
    # thus incurs a "trade" per validators.py's diff-based trade count)
    # when the dial crosses a full grid increment, not on every wiggle.
    exposure = (exposure / rebalance_step).round() * rebalance_step
    return exposure.fillna(0.0)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
