"""Strategy: Ehlers MESA Sine Wave cycle-turn entry, confirmed by an EMA trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-069):
John Ehlers' MESA Sine Wave (Maximum Entropy Spectral Analysis) estimates the
market's dominant cycle and plots two lines -- Sine (in-phase) and LeadSine
(45-degree phase-advanced projection). When Sine crosses above LeadSine while
both sit below the zero centerline, it marks a leading (1-3 bar early per the
source) bullish cycle turn. Per theindicatorlab.com's own worked entry/exit
rule: "Wait for Sine Wave to cross above Lead Sine Wave while both are below
the zero line. Confirm with price breaking above ... a key moving average (I
use 20 EMA)." Exit: "Take partial profits when Sine Wave crosses below the
Lead Sine Wave." This repo already tested Ehlers' MESA STOCHASTIC (a
countertrend oscillator built on the same Hilbert-transform cycle-extraction
machinery, id=2026-09-04-118, rejected) -- the Sine Wave is a structurally
distinct construction (raw in-phase/quadrature phase-angle sine projections,
not a stochastic-normalized oscillator) and this test uses a cycle-turn
*trend-confirmation* entry rather than a countertrend oscillator-threshold
entry, so it is not a re-test of the same idea.

Signal logic
------------
- Compute the classic Ehlers homodyne-discriminator dominant-cycle Sine Wave
  / Lead Sine Wave pair (recursive IIR filters over price, as originally
  published in Ehlers' "Rocket Science for Traders").
- Entry (long): Sine crosses above LeadSine while both are <= 0 (cycle-mode
  bullish turn) AND close > EMA(trend_window) (source's own trend
  confirmation filter).
- Exit: Sine crosses back below LeadSine (the oscillator's own "death
  cross"), OR close falls back below the EMA trend filter, OR a
  max_hold_days time-stop (avoid indefinite holds through a subsequent
  strong-trend regime where the cycle-oscillator naturally stops
  oscillating around zero, per the source's own "whipsaws ... trending
  markets" caveat).

Interface contract for validators/grid_test (see RESEARCH_LOOP.md Step 5):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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


def _mesa_sine_wave(price: pd.Series):
    """Ehlers homodyne-discriminator MESA Sine Wave / Lead Sine Wave.

    Returns (sine, lead_sine) as np.ndarray aligned to `price`'s index.
    Faithful reimplementation of Ehlers' published recursive filter chain
    (smoother -> detrender -> quadrature -> homodyne discriminator -> period
    -> phase -> sine/lead-sine), operating on daily-bar closes.
    """
    p = price.to_numpy(dtype=float)
    n = len(p)

    smooth = np.zeros(n)
    detrender = np.zeros(n)
    q1 = np.zeros(n)
    i1 = np.zeros(n)
    ji = np.zeros(n)
    jq = np.zeros(n)
    i2 = np.zeros(n)
    q2 = np.zeros(n)
    re = np.zeros(n)
    im = np.zeros(n)
    period = np.full(n, 15.0)
    phase = np.zeros(n)
    sine = np.zeros(n)
    lead_sine = np.zeros(n)

    for t in range(n):
        if t >= 3:
            smooth[t] = (4 * p[t] + 3 * p[t - 1] + 2 * p[t - 2] + p[t - 3]) / 10.0
        else:
            smooth[t] = p[t]

        if t >= 6:
            adj = 0.075 * period[t - 1] + 0.54
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
            i1[t] = detrender[t - 3] if t >= 3 else detrender[t]

            ji[t] = (
                0.0962 * i1[t]
                + 0.5769 * i1[t - 2]
                - 0.5769 * i1[t - 4]
                - 0.0962 * i1[t - 6]
            ) * adj
            jq[t] = (
                0.0962 * q1[t]
                + 0.5769 * q1[t - 2]
                - 0.5769 * q1[t - 4]
                - 0.0962 * q1[t - 6]
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
                new_period = 360.0 / math.degrees(math.atan2(im[t], re[t]))
            else:
                new_period = period[t - 1]
            if new_period > 1.5 * period[t - 1]:
                new_period = 1.5 * period[t - 1]
            if new_period < 0.67 * period[t - 1]:
                new_period = 0.67 * period[t - 1]
            new_period = min(max(new_period, 6.0), 50.0)
            period[t] = 0.2 * new_period + 0.8 * period[t - 1]

            if i1[t] != 0:
                raw_phase = math.degrees(math.atan(q1[t] / i1[t]))
            else:
                raw_phase = 90.0 if q1[t] > 0 else -90.0
            if i1[t] < 0:
                raw_phase += 180.0
            if raw_phase < 0:
                raw_phase += 360.0
            phase[t] = raw_phase

            sine[t] = math.sin(math.radians(phase[t]))
            lead_sine[t] = math.sin(math.radians(phase[t] + 45.0))
        else:
            period[t] = period[t - 1] if t > 0 else 15.0

    return sine, lead_sine


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 20,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sine, lead_sine = _mesa_sine_wave(close)
    sine = pd.Series(sine, index=close.index)
    lead_sine = pd.Series(lead_sine, index=close.index)

    ema_trend = close.ewm(span=trend_window, adjust=False).mean()

    bull_cross = (sine > lead_sine) & (sine.shift(1) <= lead_sine.shift(1))
    both_below_zero = (sine <= 0) & (lead_sine <= 0)
    entry = bull_cross & both_below_zero & (close > ema_trend)

    bear_cross = (sine < lead_sine) & (sine.shift(1) >= lead_sine.shift(1))
    exit_trend_break = close <= ema_trend

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(bear_cross.iloc[i]) or bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
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
