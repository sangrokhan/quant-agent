"""Strategy: Fractal Adaptive Moving Average (FRAMA) ATR-band breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-132):
John Ehlers' FRAMA (2005) is an EMA whose smoothing constant alpha is
recomputed every bar from the fractal dimension D of price over the last
`length` bars (split into two half-windows N1/N2 plus the full window N3;
D = (log(N1+N2) - log(N3)) / log(2)), giving alpha = exp(-4.6*(D-1)) --
behaving like a fast EMA in clean trending markets (D near 1) and a very
slow one in choppy/congested markets (D near 2). Per
[oxfordstrat.com](https://oxfordstrat.com/trading-strategies/fractal-adaptive-moving-average/)'s
own systematic trading-strategy specification (Ehlers' original design,
tested on 42 futures markets over 36 years): entry is an ATR-band breakout
around the FRAMA line -- long when close crosses above
FRAMA + atr_band*ATR(length); trend-exit when close crosses back below
FRAMA - 0.5*atr_band*ATR(length) (a tighter inner band, avoiding
whipsaw-exit at the same level as entry). This test adapts the
long-only side of that exact rule to daily equity/crypto bars (the source
tests 42 futures markets; no prior FRAMA strategy in this repo).

Signal logic
------------
- length: FRAMA/ATR lookback window (default 20, must be even).
- atr_band: ATR multiple for the entry band (default 1.5, sensitivity
  range in the source is 0.0-6.0).
- Long entry: close > FRAMA + atr_band * ATR(length) (source's Entry_Upper_Band
  breakout rule).
- Exit: close < FRAMA - 0.5*atr_band*ATR(length) (source's Exit_Lower_Band
  trend-exit rule), OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py) and
grid_test.py: generate_signals/generate_returns take price_df plus keyword
params.
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


def _rolling_max_min(arr: np.ndarray, window: int) -> tuple[np.ndarray, np.ndarray]:
    """Vectorized rolling max/min via numpy stride tricks (no pandas overhead)."""
    n = len(arr)
    if n < window:
        return np.full(n, np.nan), np.full(n, np.nan)
    shape = (n - window + 1, window)
    strides = (arr.strides[0], arr.strides[0])
    windows = np.lib.stride_tricks.as_strided(arr, shape=shape, strides=strides)
    rmax = np.concatenate([np.full(window - 1, np.nan), windows.max(axis=1)])
    rmin = np.concatenate([np.full(window - 1, np.nan), windows.min(axis=1)])
    return rmax, rmin


def _frama(df: pd.DataFrame, length: int) -> pd.Series:
    """Ehlers Fractal Adaptive Moving Average on (high+low)/2 (numpy-vectorized windows)."""
    if length % 2 != 0:
        length += 1
    half = length // 2
    price = ((df["high"] + df["low"]) / 2.0).to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    n = len(df)

    full_max, full_min = _rolling_max_min(high, length)[0], _rolling_max_min(low, length)[1]

    # N1: rolling max/min of the FIRST half of each length-window -> equivalent to a
    # rolling max/min of window `half` evaluated `half` bars before the window end.
    h_max_half, l_min_half = _rolling_max_min(high, half)[0], _rolling_max_min(low, half)[1]
    n1_max = np.roll(h_max_half, half)
    n1_min = np.roll(l_min_half, half)
    n1_max[:half] = np.nan
    n1_min[:half] = np.nan
    # N2: second half of the length-window ending at i == half-window ending at i.
    n2_max = h_max_half
    n2_min = l_min_half

    n1 = (n1_max - n1_min) / half
    n2 = (n2_max - n2_min) / half
    n3 = (full_max - full_min) / length

    with np.errstate(invalid="ignore", divide="ignore"):
        valid = (n1 > 0) & (n2 > 0) & (n3 > 0)
        d = np.where(valid, (np.log(n1 + n2) - np.log(n3)) / np.log(2), 1.0)
    alpha = np.exp(-4.6 * (d - 1))
    alpha = np.clip(alpha, 0.01, 1.0)

    frama = np.empty(n, dtype=float)
    prev = price[0] if n else float("nan")
    for i in range(n):
        if i < length or np.isnan(alpha[i]):
            frama[i] = price[i]
            prev = frama[i]
        else:
            cur = alpha[i] * price[i] + (1 - alpha[i]) * prev
            frama[i] = cur
            prev = cur

    return pd.Series(frama, index=df.index)


def _atr(df: pd.DataFrame, length: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(length).mean()


def generate_signals(
    price_df: pd.DataFrame,
    length: int = 20,
    atr_band: float = 1.5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    frama = _frama(df, length)
    atr = _atr(df, length)

    entry_upper = frama + atr_band * atr
    exit_lower = frama - 0.5 * atr_band * atr

    entry_signal = close > entry_upper
    exit_signal = close < exit_lower

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_now = bool(exit_signal.iloc[i]) if pd.notna(exit_signal.iloc[i]) else False
            if exit_now or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            entry_now = bool(entry_signal.iloc[i]) if pd.notna(entry_signal.iloc[i]) else False
            if entry_now:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    length: int = 20,
    atr_band: float = 1.5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(df, length=length, atr_band=atr_band, max_hold_days=max_hold_days)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
