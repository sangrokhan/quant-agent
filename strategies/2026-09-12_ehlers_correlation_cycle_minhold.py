"""Strategy: Ehlers Correlation Cycle / Market State regime-switch, with a
minimum-hold-days filter to reduce whipsaw around the 9-degree flatline
threshold.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Direct follow-up to near-miss 2026-09-12-138 (Ehlers Correlation Cycle /
Market State phasor regime-switch, source:
https://www.mesasoftware.com/papers/CORRELATION%20AS%20A%20CYCLE%20INDICATOR.pdf).
That strategy full-sample Sharpe missed the >=1.0 threshold on both QQQ
(0.969) and SPY (0.926) by a narrow margin, and its own backtest report
attributed the shortfall to "frequent whipsaw around the 9-degree flatline
threshold during choppy/high-vol periods" driving trade counts of 246-258
(~weekly turnover) that dragged on transaction costs (SPY TC-survival
0.494, just below the 0.5 threshold). The report explicitly suggested
"adding a minimum-hold-period filter to reduce whipsaw" as a future fix --
this iteration implements exactly that, reusing the identical
Correlation-Cycle/Angle/State math (unchanged) but suppressing new
entry/exit signal flips for `min_hold_days` bars after any position change,
same fix pattern this repo has previously used successfully for Klinger
(2026-09-04-085), ZLEMA (2026-09-06-171), and Accelerator Oscillator
(2026-09-06-174) near-misses.

Signal logic: identical underlying state machine (state=0 cycle mode,
state=+1 trend-up, state=-1 trend-down; long when state==+1 OR (state==0
AND angle<0)) as 2026-09-12-138, but a raw target-position series is
computed first, then a `min_hold_days`-bar hysteresis is applied: once a
position transition (flat->long or long->flat) occurs, ignore any opposite
target-position signal until `min_hold_days` bars have elapsed since that
transition.

Interface contract for validators/grid_test:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _correlation_cycle(close: np.ndarray, period: int):
    """Ehlers' Correlation Cycle / Angle / State (unchanged from 2026-09-12-138)."""
    n = len(close)
    real = np.full(n, np.nan)
    imag = np.full(n, np.nan)
    angle = np.full(n, np.nan)
    state = np.zeros(n, dtype=int)

    cos_wave = np.array([math.cos(math.radians(360 * k / period)) for k in range(period)])
    neg_sin_wave = np.array([-math.sin(math.radians(360 * k / period)) for k in range(period)])

    for t in range(period - 1, n):
        window = close[t - period + 1 : t + 1][::-1]
        x = window
        y_cos = cos_wave
        y_sin = neg_sin_wave

        sx = x.sum()
        sxx = (x * x).sum()

        sy_c = y_cos.sum()
        sxy_c = (x * y_cos).sum()
        syy_c = (y_cos * y_cos).sum()
        denom_c = (period * sxx - sx * sx) * (period * syy_c - sy_c * sy_c)
        r = (period * sxy_c - sx * sy_c) / math.sqrt(denom_c) if denom_c > 0 else np.nan

        sy_s = y_sin.sum()
        sxy_s = (x * y_sin).sum()
        syy_s = (y_sin * y_sin).sum()
        denom_s = (period * sxx - sx * sx) * (period * syy_s - sy_s * sy_s)
        im = (period * sxy_s - sx * sy_s) / math.sqrt(denom_s) if denom_s > 0 else np.nan

        real[t] = r
        imag[t] = im

        if im is not None and not np.isnan(im) and im != 0:
            ang = 90 + math.degrees(math.atan(r / im))
        else:
            ang = np.nan
        if im is not None and not np.isnan(im) and im > 0:
            ang = ang - 180

        prev_angle = angle[t - 1] if t > period - 1 else np.nan
        if not np.isnan(prev_angle) and not np.isnan(ang) and (prev_angle - ang) < 270 and ang < prev_angle:
            ang = prev_angle

        angle[t] = ang

        if t > period - 1 and not np.isnan(angle[t]) and not np.isnan(angle[t - 1]):
            d = abs(angle[t] - angle[t - 1])
            if d < 9 and angle[t] < 0:
                state[t] = -1
            elif d < 9 and angle[t] >= 0:
                state[t] = 1
            else:
                state[t] = 0

    return real, imag, angle, state


def generate_signals(
    price_df: pd.DataFrame,
    period: int = 20,
    min_hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series with min-hold hysteresis."""
    df = _prep(price_df)
    close = df["close"].to_numpy(dtype=float)
    n = len(close)

    _real, _imag, angle, state = _correlation_cycle(close, period)

    raw_target = np.zeros(n, dtype=int)
    for i in range(n):
        if state[i] == 1:
            raw_target[i] = 1
        elif state[i] == 0 and not np.isnan(angle[i]) and angle[i] < 0:
            raw_target[i] = 1
        else:
            raw_target[i] = 0

    position = np.zeros(n, dtype=int)
    current = 0
    last_change_idx = -min_hold_days  # allow immediate first entry
    for i in range(n):
        if raw_target[i] != current and (i - last_change_idx) >= min_hold_days:
            current = raw_target[i]
            last_change_idx = i
        position[i] = current

    return pd.Series(position, index=df.index, dtype=int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
