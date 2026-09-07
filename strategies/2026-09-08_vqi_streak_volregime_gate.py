"""Strategy: VQI streak confirmation + realized-volatility regime gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-043):
Direct follow-up to the near-miss Volatility Quality Index (VQI, Thomas
Stridsman) streak-confirmation strategy already in this repo
(id=2026-09-08-028, strategies/2026-09-08_vqi_streak_confirmation.py):
QQQ reached a near-miss full-sample Sharpe of 0.941 (MDD/TC/WF/param-sens
all passed) while SPY failed decisively and crypto failed decisively
(0/48). This repo's established, previously-productive fix pattern
(applied successfully to KAMA/ATR-band 2026-09-06-183 and Elder-Ray Bull
Power 2026-09-06-176, both direct-follow-up near-miss rescues) is to add
an explicit realized-volatility regime gate restricting entries to the
low-volatility tercile, using the identical construction already
established in this repo's accepted
`strategies/2026-09-03_bb_meanrev_qqq_volregime.py` (20-day realized vol
<= its own trailing 1-year rolling median defines "low-vol regime").

Identical VQI entry/exit/streak logic to the base strategy is kept
unchanged; only a `close`-independent regime gate is added on top,
testing whether narrowing to the low-vol regime alone rescues the
full-sample Sharpe from its 0.941 near-miss to above the 1.0 threshold
(analogous to how the base strategy's underlying grid showed edge
concentrated more heavily in calmer vol conditions).

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py).
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


def _true_range(df: pd.DataFrame) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _vqi_smoothed(df: pd.DataFrame, vqi_length: int, smoothing_length: int) -> pd.Series:
    tr = _true_range(df)
    direction = np.sign(df["close"] - df["open"])
    weighted_vol = tr * direction
    vqi_raw = weighted_vol.ewm(span=vqi_length, min_periods=vqi_length, adjust=False).mean()
    vqi_smoothed = vqi_raw.ewm(span=smoothing_length, min_periods=smoothing_length, adjust=False).mean()
    return vqi_smoothed


def _low_vol_regime(close: pd.Series, vol_window: int, median_window: int) -> pd.Series:
    daily_ret = close.pct_change()
    realized_vol = daily_ret.rolling(vol_window).std()
    trailing_median = realized_vol.rolling(median_window, min_periods=vol_window).median()
    return (realized_vol <= trailing_median).fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    vqi_length: int = 14,
    smoothing_length: int = 5,
    streak_bars: int = 10,
    max_hold_days: int = 15,
    vol_window: int = 20,
    median_window: int = 252,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    vqi = _vqi_smoothed(df, vqi_length, smoothing_length)
    low_vol = _low_vol_regime(close, vol_window, median_window)

    diff = vqi.diff()
    rising = diff > 0
    falling = diff < 0

    rising_streak = rising.rolling(streak_bars).sum() == streak_bars
    falling_streak = falling.rolling(streak_bars).sum() == streak_bars

    valid = vqi.notna() & rising_streak.notna() & falling_streak.notna()

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(len(df)):
        if not valid.iloc[i]:
            position.iloc[i] = 0
            continue
        if in_position:
            held = i - entry_idx
            # exit stays active regardless of regime (only entry is gated)
            if bool(falling_streak.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(rising_streak.iloc[i]) and bool(low_vol.iloc[i]):
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
