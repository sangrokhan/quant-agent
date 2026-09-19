"""Strategy: 52-Week High breakout, low-vol-regime-gated, 200-day SMA exit.

Direct fix/rescue attempt for prior id 2026-09-20-054 (52-Week High
breakout + 200d-SMA-exit, near-miss REJECTED: SPY Sharpe 0.879, QQQ Sharpe
0.880, both just under the 1.0 threshold at the best shared config found
via a 42-combo search). That entry's own grid-test notes flagged the
effect as strongly concentrated in low-vol regimes (grid pass_fraction by
vol-regime: low 23/36, mid 3/36, high 3/36) and explicitly suggested "add
an explicit low-vol regime gate ... might push the low-vol-only Sharpe
over threshold" as the follow-up direction -- exactly what this iteration
implements. No new external research this sub-iteration (same source,
same disclosed rule, this is a mechanical robustness/regime-gate fix
mirroring this repo's established rescue pattern, e.g.
2026-09-16-106/2026-09-16-161).

Added gate: only take a new-52-week-high entry when trailing
vol_window-day realized volatility is at/below its own trailing
vol_lookback-day median (i.e. we are in a "low-vol" regime by this repo's
standard definition, same construction as
strategies/2026-09-03_bb_meanrev_qqq_volregime.py). If already in a
position and the regime flips to high-vol, exit early (risk-off), in
addition to the original SMA-cross exit and time-stop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (position: 1 long/0 flat)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
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
    lookback_days: int = 63,
    exit_sma_window: int = 150,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
    max_hold_days: int = 500,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median_1y = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    low_vol_regime = realized_vol <= (vol_median_1y * vol_regime_ratio)

    rolling_high = close.rolling(lookback_days, min_periods=lookback_days).max()
    is_new_high = close >= rolling_high

    sma = close.rolling(exit_sma_window).mean()
    exit_below_sma = close < sma
    exit_regime_flip = ~low_vol_regime.fillna(False)

    entry = is_new_high.fillna(False) & low_vol_regime.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_below_sma.iloc[i]) or bool(exit_regime_flip.iloc[i]) or held >= max_hold_days:
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
