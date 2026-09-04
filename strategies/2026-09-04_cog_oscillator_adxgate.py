"""Strategy: Ehlers Center of Gravity (CG) oscillator reversal, gated by ADX
ranging-regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-124):
John Ehlers' Center of Gravity oscillator (Cybernetic Analysis, 2004) computes
a near-zero-lag "balance point" of recent prices:
    CG_t = -sum_{i=0}^{N-1} (i+1) * Price[t-i]  /  sum_{i=0}^{N-1} Price[t-i]
Per the QuantWave docs (github.com/lavs9/quantwave) and ForexDominion's CoG
guide, turning points in CG lead turning points in price; the standard
trading rule crosses CG against a 1-bar-delayed copy of itself (the
"trigger" line), and both sources explicitly recommend gating cycle-based CG
signals with a trend-strength filter (ADX) since CG is a mean-reversion tool
designed for ranging/non-trending regimes, not for use during strong trends.

Signal logic
------------
- CG(cg_period) computed on close prices (formula above).
- trigger = CG shifted by 1 bar.
- ranging regime = ADX(adx_period) < adx_threshold (per source recommendation
  to "gate with ADX ... before taking cycle signals").
- Entry (long): CG crosses above trigger (CG[t] > trigger[t] and
  CG[t-1] <= trigger[t-1]) while CG is at/below -extreme_threshold (an
  oversold turning point per the reversal-strategy rule) AND we're in a
  ranging regime.
- Exit: CG crosses back below trigger, OR CG rises above +extreme_threshold,
  OR max_hold_days elapses, whichever comes first.
- Long-only, flat otherwise.

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


def _center_of_gravity(close: pd.Series, period: int) -> pd.Series:
    weights = np.arange(1, period + 1, dtype=float)  # (i+1) for i=0..N-1, i=0 is most recent
    num = close.rolling(period).apply(
        lambda w: float(np.dot(weights, w[::-1])), raw=True
    )
    den = close.rolling(period).sum()
    cg = -num / den.replace(0.0, np.nan)
    return cg


def _adx(df: pd.DataFrame, period: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)

    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)

    atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    plus_di = 100.0 * plus_dm.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean() / atr.replace(0.0, np.nan)
    minus_di = 100.0 * minus_dm.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean() / atr.replace(0.0, np.nan)

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    adx = dx.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    return adx


def generate_signals(
    price_df: pd.DataFrame,
    cg_period: int = 10,
    extreme_threshold: float = 0.0,
    adx_period: int = 14,
    adx_threshold: float = 25.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    cg = _center_of_gravity(close, cg_period)
    trigger = cg.shift(1)
    adx = _adx(df, adx_period)
    ranging = adx < adx_threshold

    cross_up = (cg > trigger) & (cg.shift(1) <= trigger.shift(1))
    cross_down = (cg < trigger) & (cg.shift(1) >= trigger.shift(1))

    entry_trigger = cross_up & (cg <= -extreme_threshold) & ranging.fillna(False)

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        cgi = cg.iloc[i]
        if in_pos:
            hold_count += 1
            exit_now = bool(cross_down.iloc[i]) if pd.notna(cross_down.iloc[i]) else False
            overbought_exit = bool(cgi > extreme_threshold) if pd.notna(cgi) else False
            if exit_now or overbought_exit or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]) if pd.notna(entry_trigger.iloc[i]) else False:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    cg_period: int = 10,
    extreme_threshold: float = 0.0,
    adx_period: int = 14,
    adx_threshold: float = 25.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        cg_period=cg_period,
        extreme_threshold=extreme_threshold,
        adx_period=adx_period,
        adx_threshold=adx_threshold,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
