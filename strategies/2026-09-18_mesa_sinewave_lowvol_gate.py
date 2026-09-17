"""Strategy: Ehlers MESA Sine Wave cycle-turn entry, rescued with an explicit
realized-volatility regime gate (only trade in the low-vol tercile).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-069 for the
prior attempt, and this iteration's id for the rescue):
The original MESA Sine Wave cycle-turn strategy (2026-09-05-069,
strategies/2026-09-05_mesa_sinewave_cycle_turn.py) was REJECTED on full-sample
Sharpe (0.29 QQQ / 0.45 SPY vs 1.0 threshold) and transaction-cost survival,
but its own grid-test breakdown showed the ENTIRE edge was concentrated in
the low-realized-vol tercile: "Grid test ... by_vol_regime: low 18/36 (50%,
ALL passes concentrated here), mid 0/36, high 0/36 ... best_cell:
trend_window=20/max_hold_days=10, SPY, low-vol, Sharpe=1.782 ... The
strategy's entire edge lives in the low-realized-vol tercile (consistent
Sharpe 1.1-1.8, tight MDD 0.02-0.06 across all param combos there) ... Worth
revisiting gated by an explicit low-vol-regime filter". This strategy is that
direct rescue attempt: add an explicit 20-day realized-vol-vs-trailing-median
gate (same construction as strategies/2026-09-03_bb_meanrev_qqq_volregime.py)
so the strategy only takes MESA Sine Wave cycle-turn entries when in a
low-vol regime, going flat otherwise, instead of trading unconditionally
through mid/high-vol whipsaw regimes where the source itself warns the
oscillator "whipsaws badly in choppy, directionless markets".

Signal logic
------------
- Same Ehlers homodyne-discriminator Sine/LeadSine construction and
  trend-confirmation entry/exit as 2026-09-05-069 (see that file for detail).
- NEW: 20-day realized volatility (std of daily log returns, annualized) vs
  its trailing `vol_lookback`-day median -> "low-vol regime" when current
  vol <= `vol_regime_ratio` x that median. Entries are only allowed while in
  a low-vol regime; an open position is force-exited (in addition to the
  existing bear-cross/trend-break/max-hold exits) if the regime flips to
  mid/high-vol, mirroring 2026-09-03-001's regime-flip risk-off exit.

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

    Identical implementation to strategies/2026-09-05_mesa_sinewave_cycle_turn.py
    (kept as a faithful copy so this file is self-contained / independently
    testable without importing a sibling strategy module).
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


def _low_vol_regime(close: pd.Series, vol_window: int, vol_lookback: int, vol_regime_ratio: float) -> pd.Series:
    log_ret = np.log(close).diff()
    realized_vol = log_ret.rolling(vol_window).std() * math.sqrt(252)
    trailing_median = realized_vol.rolling(vol_lookback, min_periods=max(20, vol_lookback // 4)).median()
    low_vol = realized_vol <= (vol_regime_ratio * trailing_median)
    return low_vol.fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 20,
    max_hold_days: int = 15,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sine, lead_sine = _mesa_sine_wave(close)
    sine = pd.Series(sine, index=close.index)
    lead_sine = pd.Series(lead_sine, index=close.index)

    ema_trend = close.ewm(span=trend_window, adjust=False).mean()
    low_vol = _low_vol_regime(close, vol_window, vol_lookback, vol_regime_ratio)

    bull_cross = (sine > lead_sine) & (sine.shift(1) <= lead_sine.shift(1))
    both_below_zero = (sine <= 0) & (lead_sine <= 0)
    entry = bull_cross & both_below_zero & (close > ema_trend) & low_vol

    bear_cross = (sine < lead_sine) & (sine.shift(1) >= lead_sine.shift(1))
    exit_trend_break = close <= ema_trend
    exit_regime_flip = ~low_vol

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if (
                bool(bear_cross.iloc[i])
                or bool(exit_trend_break.iloc[i])
                or bool(exit_regime_flip.iloc[i])
                or held >= max_hold_days
            ):
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
