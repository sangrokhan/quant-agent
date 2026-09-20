"""Strategy: LBR 3/10 Oscillator signal-line crossover, gated by a low-vol regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-121):
Direct rescue/follow-up to rejected id 2026-09-20-120 (LBR 3/10 Oscillator,
unconditional full-period Sharpe 0.540 QQQ / 0.618 SPY, both failed the 1.0
threshold; net-of-cost Sharpe ~0.2 also failed). That iteration's Step 6
grid showed the edge is decisively regime-dependent: low-vol-tercile cells
passed at 0.594 pass_fraction vs mid 0.25 vs high 0.031 (best_cell Sharpe
1.989 in a low-vol cell, worst_cell Sharpe -0.438 in a high-vol cell). This
iteration applies the identical vol-regime-gate pattern already proven for
2026-09-03-001 (BB mean-reversion + vol-regime filter, accepted): only take
the 3/10 Oscillator's golden-cross long signal while realized volatility is
at/below its own trailing-median (low-vol regime); force flat whenever the
regime flips to elevated vol, even mid-position.

Signal logic
------------
- fast_line = SMA(close, fast_window) - SMA(close, slow_window)
- signal_line = SMA(fast_line, signal_window)
- realized_vol = rolling std of daily log returns (vol_window), annualized
- vol_median = trailing rolling median of realized_vol over vol_lookback
- low_vol_regime = realized_vol <= vol_median * vol_regime_ratio
- Entry (long): fast_line crosses above signal_line (golden cross) AND
  low_vol_regime is True
- Exit (flat): fast_line crosses below signal_line (dead cross) OR the
  regime flips out of low-vol (risk-off exit) while in a position

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index.
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


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 3,
    slow_window: int = 10,
    signal_window: int = 9,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fast_sma = close.rolling(fast_window).mean()
    slow_sma = close.rolling(slow_window).mean()
    fast_line = fast_sma - slow_sma
    signal_line = fast_line.rolling(signal_window).mean()

    above = fast_line > signal_line
    prev_above = above.shift(1).fillna(False)
    golden_cross = above & (~prev_above)
    dead_cross = (~above) & prev_above

    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    low_vol_regime = (realized_vol <= (vol_median * vol_regime_ratio)).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        regime_ok = bool(low_vol_regime.iloc[i])
        if in_position:
            if bool(dead_cross.iloc[i]) or not regime_ok:
                in_position = False
        else:
            if bool(golden_cross.iloc[i]) and regime_ok:
                in_position = True
        position.iloc[i] = 1 if in_position else 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
