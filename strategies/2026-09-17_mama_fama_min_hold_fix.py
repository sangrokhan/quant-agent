"""Strategy: MAMA/FAMA crossover with an explicit min_hold_days gate.

Hypothesis (see knowledge_base id=2026-09-17-XXX): Direct fix for
2026-09-06-101 (MAMA/FAMA crossover, accepted QQQ but SPY REJECTED as a
near-miss: Sharpe 0.649<1.0 and net-of-cost Sharpe 0.483<0.5 at 70 trades
over the sample -- i.e. the underlying MAMA/FAMA logic captures a real edge
on the same asset class (QQQ passes cleanly) but SPY whipsaws too often
around noisy near-touches of the two adaptive lines, exactly the failure
mode Ehlers' own literature describes and warns about (re-confirmed this
iteration via https://iwpfinance.com/concepts/technical-analysis/mama-fama-mesa-adaptive:
"Investors often misread small MAMA-FAMA touches as signals; meaningful
crosses are wider and less frequent").

This repo's own knowledge base already has a proven fix pattern for this
exact failure mode: id=2026-09-04-085 (Klinger Volume Oscillator, KVO)
added an explicit min_hold_days gate that ignores exit signals for the
first N days after entry, cutting trade COUNT without touching the
underlying oscillator signal, and that flipped a transaction-cost-survival
failure to a pass on SPY. This strategy applies the identical fix
mechanism to MAMA/FAMA's SPY near-miss: once a position opens, no exit
signal is honored for min_hold_days bars, reducing whipsaw-driven trade
count while preserving the crossover's genuine trend-turn detections.

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
    """Ehlers' MESA Adaptive Moving Average (identical to
    strategies/2026-09-06_mama_fama_crossover.py's implementation).
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
    max_hold_days: int = 40,
    min_hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Same MAMA/FAMA crossover logic as the original strategy, but exit
    signals (and the max-hold-days time-stop) are ignored for the first
    ``min_hold_days`` bars after entry -- the fix mechanism proven on
    2026-09-04-085 (KVO) for cutting whipsaw-driven trade count.
    """
    df = _prep(price_df)
    hl2 = (df["high"] + df["low"]) / 2.0
    close = df["close"]

    mama, fama = _mama_fama(hl2, fast_limit, slow_limit)

    cross_up = (mama > fama) & (mama.shift(1) <= fama.shift(1))
    cross_down = (mama < fama) & (mama.shift(1) >= fama.shift(1))

    entry = cross_up.fillna(False)
    exit_signal = cross_down.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if held < min_hold_days:
                # Min-hold gate: ignore exit signal and time-stop entirely
                # during the protected window.
                position.iloc[i] = 1
                continue
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
