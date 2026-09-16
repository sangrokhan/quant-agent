"""Strategy: Ehlers Adaptive SuperSmoother crossover, WITH a realized-vol
regime gate (direct fix attempt for the prior near-miss rejection).

Source: TASC (Technical Analysis of Stocks & Commodities) September 2026
Traders' Tips, John F. Ehlers "Adaptive SuperSmoother" article, re-confirmed
this iteration via https://traders.com/documentation/feedbk_docs/2026/09/traderstips.html
(TradeStation EasyLanguage code block gives the full disclosed formula:
SS = SuperSmoother(Close, Period0); ROC1 = SS - SS[1]; ROCRMS = RMS(ROC1, 81);
ROC = clip(|ROC1/ROCRMS|, 0, 2); Period = Period0*(1-0.5*ROC)^2, floor 2;
AdaptiveSS = SuperSmoother(Close, Period) computed with that per-bar period).
This matches the construction already implemented in this repo's prior
attempt (id=2026-09-12-146, strategies/2026-09-12_ehlers_adaptive_supersmoother_crossover.py).

Direct fix for 2026-09-12-146's own recorded near-miss rejection: that
entry's `notes` field says verbatim "Suggested future fix (not attempted):
explicit vol-regime gate to flatten during high realized-vol, consistent
with several prior accepted strategies." QQQ failed only on MDD (26.9% vs
25% threshold, near-miss) while passing Sharpe/TC/walk-forward/param-
sensitivity; SPY failed Sharpe (0.965 near-miss) and MDD (28.7%). This
strategy is otherwise IDENTICAL code/formula, but adds a realized-vol
regime gate (flatten whenever trailing `vol_window`-day realized vol is
above `vol_regime_ratio` times its trailing `vol_lookback`-day median) on
top of the existing long/flat crossover + min_hold_days hysteresis, the
same regime-gate pattern used successfully in
strategies/2026-09-03_bb_meanrev_qqq_volregime.py and several EWMA/
Parkinson/Garman-Klass/Rogers-Satchell vol-targeting overlays accepted this
same cron trigger's earlier iterations.

Interface contract (see validation/grid_test.py, validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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


def _supersmoother(src: pd.Series, period: float) -> pd.Series:
    """Ehlers 2-pole SuperSmoother with a FIXED period (scalar)."""
    n = len(src)
    out = np.zeros(n)
    a1 = math.exp(-1.414 * math.pi / period)
    b1 = 2 * a1 * math.cos(1.414 * math.pi / period)
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3
    vals = src.values
    for i in range(n):
        if i < 2 or np.isnan(vals[i - 1]) or np.isnan(vals[i - 2]):
            out[i] = vals[i]
        else:
            out[i] = c1 * (vals[i] + vals[i - 1]) / 2 + c2 * out[i - 1] + c3 * out[i - 2]
    return pd.Series(out, index=src.index)


def _supersmoother_adaptive(src: pd.Series, periods: pd.Series) -> pd.Series:
    """Ehlers 2-pole SuperSmoother with a per-bar-varying period series."""
    n = len(src)
    out = np.zeros(n)
    vals = src.values
    p = periods.values
    for i in range(n):
        period = max(2.0, float(p[i])) if not np.isnan(p[i]) else 20.0
        a1 = math.exp(-1.414 * math.pi / period)
        b1 = 2 * a1 * math.cos(1.414 * math.pi / period)
        c2 = b1
        c3 = -a1 * a1
        c1 = 1 - c2 - c3
        if i < 2 or np.isnan(vals[i - 1]) or np.isnan(vals[i - 2]):
            out[i] = vals[i]
        else:
            out[i] = c1 * (vals[i] + vals[i - 1]) / 2 + c2 * out[i - 1] + c3 * out[i - 2]
    return pd.Series(out, index=src.index)


def generate_signals(
    price_df: pd.DataFrame,
    base_period: int = 20,
    rms_length: int = 81,
    min_hold_days: int = 5,
    max_hold_days: int = 60,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fixed_ss = _supersmoother(close, float(base_period))

    roc = fixed_ss.diff()
    rms = (roc ** 2).rolling(rms_length).mean() ** 0.5
    scaled_roc = (roc / rms.replace(0, np.nan)).clip(-2, 2).fillna(0.0)
    factor = (1 - 0.5 * scaled_roc) ** 2
    adaptive_period = (base_period * factor).clip(lower=2.0)

    adaptive_ss = _supersmoother_adaptive(close, adaptive_period)

    raw_long_signal = adaptive_ss > fixed_ss

    # Realized-vol regime gate: trailing vol_window-day realized vol
    # (annualized) vs its trailing vol_lookback-day median.
    daily_log_ret = (close / close.shift(1)).apply(
        lambda r: math.log(r) if r and r > 0 else None
    ).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    low_vol_regime = (realized_vol <= (vol_median * vol_regime_ratio)).fillna(False)

    raw_long = raw_long_signal & low_vol_regime

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            # Exit on: signal turns bearish (past hysteresis), OR regime
            # flips to high-vol (immediate risk-off, no hysteresis), OR
            # max hold reached.
            regime_flip_exit = not bool(low_vol_regime.iloc[i])
            want_flat = (not bool(raw_long_signal.iloc[i])) and held >= min_hold_days
            if want_flat or regime_flip_exit or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(raw_long.iloc[i]):
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
