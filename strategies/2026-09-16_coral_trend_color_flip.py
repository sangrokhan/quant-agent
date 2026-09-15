"""Strategy: Coral Trend Indicator (LazyBear) trend-color-flip.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
The Coral Trend Indicator (LazyBear) is a cascade of six one-pole EMA
smoothing stages (i1..i6, each fed from the previous stage's output),
recombined via cubic-polynomial coefficients derived from a lag-
compensation constant D (default 0.4), producing a single low-lag trend
line ("Cto"). Per the exact disclosed Pine v4 source
(https://www.tradingview.com/script/AzQo1gRi-Coral-Trend-Indicator-LazyBear/):

    di = (sm-1)/2 + 1;  c1 = 2/(di+1);  c2 = 1-c1
    c3 = 3*(D^2 + D^3);  c4 = -3*(2*D^2 + D + D^3);  c5 = 3*D + 1 + D^3 + 3*D^2
    i1 = c1*src + c2*i1[1]   (and i2..i6 each = c1*i(k-1) + c2*i(k)[1])
    Cto = -D^3*i6 + c3*i5 + c4*i4 + c5*i3

Per the source's own disclosed rule: the indicator plots as a stepline
whose color flips green ("raise") when Cto is rising bar-over-bar and red
("fall") when falling; the disclosed buy/sell signal is the color-flip
event itself (shift_up = color flips from fall to raise). This is
distinct from every other cascaded/multi-stage-smoothing trend line
already tested in this repo (T3, TEMA, Rainbow MA, GMMA) via its unique
cubic-polynomial recombination of 6 EMA stages rather than a simple
weighted sum or cascade average. First Coral Trend strategy in this repo.

Signal logic
------------
- Long (position=1) whenever Cto is in a rising streak that began with a
  color-flip-up event (Cto_t > Cto_{t-1} after a prior falling streak);
  exit on the mirror color-flip-down event (Cto starts falling), or a
  max_hold_days time-stop. Long-only per this repo's contract.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _coral_trend(close: pd.Series, sm: int, cd: float) -> pd.Series:
    di = (sm - 1.0) / 2.0 + 1.0
    c1 = 2.0 / (di + 1.0)
    c2 = 1.0 - c1
    c3 = 3.0 * (cd * cd + cd * cd * cd)
    c4 = -3.0 * (2.0 * cd * cd + cd + cd * cd * cd)
    c5 = 3.0 * cd + 1.0 + cd * cd * cd + 3.0 * cd * cd

    src = close.to_numpy()
    n = len(src)
    i1 = np.zeros(n)
    i2 = np.zeros(n)
    i3 = np.zeros(n)
    i4 = np.zeros(n)
    i5 = np.zeros(n)
    i6 = np.zeros(n)

    for t in range(n):
        prev_i1 = i1[t - 1] if t > 0 else src[t]
        prev_i2 = i2[t - 1] if t > 0 else src[t]
        prev_i3 = i3[t - 1] if t > 0 else src[t]
        prev_i4 = i4[t - 1] if t > 0 else src[t]
        prev_i5 = i5[t - 1] if t > 0 else src[t]
        prev_i6 = i6[t - 1] if t > 0 else src[t]

        i1[t] = c1 * src[t] + c2 * prev_i1
        i2[t] = c1 * i1[t] + c2 * prev_i2
        i3[t] = c1 * i2[t] + c2 * prev_i3
        i4[t] = c1 * i3[t] + c2 * prev_i4
        i5[t] = c1 * i4[t] + c2 * prev_i5
        i6[t] = c1 * i5[t] + c2 * prev_i6

    cto = -(cd ** 3) * i6 + c3 * i5 + c4 * i4 + c5 * i3
    return pd.Series(cto, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    sm: int = 21,
    cd: float = 0.4,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series from the Coral Trend
    color-flip rule.
    """
    df = _prep(price_df)
    close = df["close"]
    cto = _coral_trend(close, sm, cd)

    rising = cto > cto.shift(1)
    falling = cto < cto.shift(1)

    n = len(df)
    color_state = np.zeros(n, dtype=int)  # 1 = raise/green, -1 = fall/red, 0 = flat/na
    rising_arr = rising.to_numpy()
    falling_arr = falling.to_numpy()
    for i in range(n):
        if rising_arr[i]:
            color_state[i] = 1
        elif falling_arr[i]:
            color_state[i] = -1
        else:
            color_state[i] = color_state[i - 1] if i > 0 else 0

    shift_up = np.zeros(n, dtype=bool)
    shift_dn = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if color_state[i - 1] == -1 and color_state[i] == 1:
            shift_up[i] = True
        if color_state[i - 1] == 1 and color_state[i] == -1:
            shift_dn[i] = True

    pos = np.zeros(n, dtype=int)
    in_pos = False
    hold = 0
    for i in range(n):
        if in_pos:
            hold += 1
            if shift_dn[i] or hold > max_hold_days:
                in_pos = False
                hold = 0
            else:
                pos[i] = 1
        else:
            if shift_up[i]:
                in_pos = True
                hold = 1
                pos[i] = 1
    return pd.Series(pos, index=df.index)


def generate_returns(
    price_df: pd.DataFrame,
    sm: int = 21,
    cd: float = 0.4,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(df, sm=sm, cd=cd, max_hold_days=max_hold_days)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)
    return position.shift(1).fillna(0) * daily_ret
