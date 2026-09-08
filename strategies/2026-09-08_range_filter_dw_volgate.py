"""Strategy: Range Filter [DW] trend-following, gated by a low-vol regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-168):
Direct follow-up to near-miss 2026-09-05-018 (plain Range Filter [DW]
crossover): the original grid showed a striking regime split -- low-vol
tercile passed 36/36 cells, mid-vol 18/36, high-vol only 1/36 -- and the
QQQ full-sample config missed the Sharpe threshold only marginally (0.957 vs
1.0 required). This strongly suggests the strategy's edge is real but is
being diluted by high-vol-regime whipsaws dragging down the full-sample
average, exactly the same fix pattern already validated in this repo for
KAMA/ATR-band (2026-09-06-183, accepted after adding a vol gate) and VQI
streak (2026-09-08-044, accepted after adding a vol gate). This variant adds
an explicit realized-volatility regime gate (20d realized vol <= trailing
1yr median, identical construction to the repo's other vol-gated strategies)
restricting entries to the low-vol regime, keeping the Range Filter [DW]
entry/exit logic completely unchanged otherwise -- isolating whether the
regime gate alone rescues the near-miss.

Signal logic
------------
- Same Range Filter [DW] construction and rising-streak entry/exit as
  2026-09-05-018.
- Additional gate: only allow NEW entries when 20-day realized volatility of
  daily log returns is <= its own trailing 252-day median (low-vol regime).
  Existing positions are NOT force-exited on a regime flip (unlike some
  other vol-gated variants in this repo) -- only entry is gated, since the
  original grid showed mid-vol cells still passed 50% of the time, so a
  hard exit-on-regime-flip may be over-restrictive; kept as entry-only gate
  to isolate the minimal fix.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position series)
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


def _range_filter(close: pd.Series, sampling_period: int, range_mult: float) -> pd.Series:
    """Compute the recursive Range Filter [DW] line."""
    avg_range = close.diff().abs().ewm(span=sampling_period, adjust=False).mean()
    wper = sampling_period * 2 - 1
    smooth_rng = avg_range.ewm(span=wper, adjust=False).mean() * range_mult

    filt = pd.Series(index=close.index, dtype=float)
    prev = close.iloc[0]
    for i in range(len(close)):
        x = close.iloc[i]
        r = smooth_rng.iloc[i]
        if pd.isna(r):
            filt.iloc[i] = x
            prev = x
            continue
        if x > prev:
            candidate = x - r
            prev = prev if candidate < prev else candidate
        else:
            candidate = x + r
            prev = prev if candidate > prev else candidate
        filt.iloc[i] = prev
    return filt


def generate_signals(
    price_df: pd.DataFrame,
    sampling_period: int = 15,
    range_mult: float = 2.5,
    max_hold_days: int = 20,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    filt = _range_filter(close, sampling_period, range_mult)
    filt_delta = filt.diff()

    upward_streak = pd.Series(0, index=close.index, dtype=int)
    streak = 0
    for i in range(len(close)):
        d = filt_delta.iloc[i]
        if pd.isna(d) or d == 0:
            pass  # hold prior streak value
        elif d > 0:
            streak += 1
        else:
            streak = 0
        upward_streak.iloc[i] = streak

    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median_1y = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    low_vol_regime = (realized_vol <= (vol_median_1y * vol_regime_ratio)).fillna(False)

    entry = (close > filt) & (upward_streak > 0) & low_vol_regime
    exit_streak_reset = upward_streak == 0

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_streak_reset.iloc[i]) or held >= max_hold_days:
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
