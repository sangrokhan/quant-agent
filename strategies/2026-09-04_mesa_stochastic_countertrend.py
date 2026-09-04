"""Strategy: Ehlers "MESA Stochastic" (My Stochastic) countertrend oscillator.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-118):
John Ehlers' MESA Stochastic ("My Stochastic", from "Predictive And
Successful Indicators") applies a 2-pole highpass filter (removes cycles
longer than a cutoff, default 48 bars) to price, then a SuperSmoother
2-pole lowpass filter to denoise it, then computes a normalized 0-1
stochastic of that filtered series over a rolling lookback window, itself
smoothed again by the SuperSmoother coefficients. Source (prorealcode.com,
converted from the original EasyLanguage) gives the exact recursive
formula and states the simple countertrend rule Ehlers demonstrated it
with: go long when MESA Stochastic crosses below the oversold threshold
(0.2), and exit/reverse when it crosses above the overbought threshold
(0.8). We implement this long-only (with exit on the overbought cross
rather than a short).

Formula (converted from the PRT source verbatim)
--------------------------------------------------
alpha1 = (cos(0.707*2*pi/48) + sin(0.707*2*pi/48) - 1) / cos(0.707*2*pi/48)
HP[i] = (1-alpha1/2)^2 * (close[i] - 2*close[i-1] + close[i-2])
        + 2*(1-alpha1)*HP[i-1] - (1-alpha1)^2*HP[i-2]

a1 = exp(-1.414*pi/10); b1 = 2*a1*cos(1.414*pi/10)
c2 = b1; c3 = -a1^2; c1 = 1 - c2 - c3
Filt[i] = c1*(HP[i]+HP[i-1])/2 + c2*Filt[i-1] + c3*Filt[i-2]

Over a rolling `length`-bar window of Filt: Stoc[i] = (Filt[i]-min)/(max-min)
MyStochastic[i] = c1*(Stoc[i]+Stoc[i-1])/2 + c2*MyStochastic[i-1] + c3*MyStochastic[i-2]

Signal logic
------------
- Entry (long): MyStochastic crosses from >=oversold to <oversold (dips
  below oversold, i.e. the classic countertrend "buy the dip" trigger).
- Exit: MyStochastic crosses back above overbought, OR a max_hold_days
  time-stop.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept params as keyword args.
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _mesa_stochastic(close: pd.Series, length: int = 20, hp_cutoff: int = 48) -> pd.Series:
    n = len(close)
    c = close.values.astype(float)

    angle1 = 0.707 * 2 * math.pi / hp_cutoff
    alpha1 = (math.cos(angle1) + math.sin(angle1) - 1) / math.cos(angle1)

    a1 = math.exp(-1.414 * math.pi / 10)
    angle2 = 1.414 * math.pi / 10
    b1 = 2 * a1 * math.cos(angle2)
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3

    hp = [0.0] * n
    filt = [0.0] * n
    stoc = [0.0] * n
    mesa = [0.0] * n

    for i in range(n):
        if i >= 2:
            hp[i] = (
                (1 - alpha1 / 2) ** 2 * (c[i] - 2 * c[i - 1] + c[i - 2])
                + 2 * (1 - alpha1) * hp[i - 1]
                - (1 - alpha1) ** 2 * hp[i - 2]
            )
        if i >= 1:
            filt[i] = c1 * (hp[i] + hp[i - 1]) / 2 + c2 * filt[i - 1] + c3 * filt[i - 2 if i >= 2 else i - 1]

        if i >= length - 1:
            window = filt[i - length + 1 : i + 1]
            hi = max(window)
            lo = min(window)
            rng = hi - lo
            stoc[i] = (filt[i] - lo) / rng if rng != 0 else 0.0
        else:
            stoc[i] = float("nan")

        if i >= 1 and not math.isnan(stoc[i]) and not math.isnan(stoc[i - 1]):
            prev1 = mesa[i - 1] if not math.isnan(mesa[i - 1]) else 0.0
            prev2 = (mesa[i - 2] if i >= 2 and not math.isnan(mesa[i - 2]) else 0.0)
            mesa[i] = c1 * (stoc[i] + stoc[i - 1]) / 2 + c2 * prev1 + c3 * prev2
        else:
            mesa[i] = float("nan")

    return pd.Series(mesa, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    length: int = 20,
    hp_cutoff: int = 48,
    oversold: float = 0.2,
    overbought: float = 0.8,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"].astype(float)

    mesa = _mesa_stochastic(close, length=length, hp_cutoff=hp_cutoff)
    mesa_prev = mesa.shift(1)

    cross_down_oversold = (mesa_prev >= oversold) & (mesa < oversold)
    cross_up_overbought = (mesa_prev <= overbought) & (mesa > overbought)

    entry = cross_down_oversold.fillna(False)
    exit_signal = cross_up_overbought.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
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
    close = df["close"].astype(float)
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
