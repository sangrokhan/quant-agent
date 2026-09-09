"""Strategy: SFP (Swing Failure Pattern) liquidity-sweep reversal, low-vol-regime gated.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-089):
Direct fix for near-miss/rejected 2026-09-09-087 (plain SFP liquidity-sweep
reversal, per https://www.quantvps.com/blog/swing-failure-pattern-strategy):
that iteration's grid test showed the pattern's edge is concentrated almost
entirely in low-realized-vol regimes (pass_fraction low=17/48 vs mid=1/48,
high=0/48 in the vol-regime-split grid), yet the unconditional rule traded
through all regimes and its full-sample Sharpe collapsed (0.31 QQQ / 0.40
SPY) versus the low-vol-regime-sliced best cell (Sharpe 2.50). This variant
adds an explicit realized-volatility regime gate -- reusing the same
construction as the already-accepted 2026-09-03_bb_meanrev_qqq_volregime.py
(20-day realized vol vs its trailing 252-day median) -- so the SFP signal
only fires while in a low-vol regime, rather than trading the raw pattern
unconditionally through all vol regimes as 2026-09-09-087 did.

Signal logic
------------
- 20-day realized volatility (std of daily log returns, annualized) compared
  to its trailing 252-day median -> "low-vol regime" when current 20d vol
  <= vol_regime_ratio x that median.
- swing_low = rolling min(low) over `swing_lookback` bars (shifted by 1,
  avoiding lookahead).
- SFP confirmation bar: low[t] < swing_low[t] (wick sweeps below prior
  swing low) AND close[t] > swing_low[t] (closes back above it, rejecting
  the breakdown) -- both required same-bar, same as 2026-09-09-087.
- Entry: long at the bar AFTER an SFP confirmation bar, ONLY IF that bar
  was in a low-vol regime (the new gate).
- Exit: close crosses back below the SFP bar's own low (stop-loss beyond
  the sweep wick extreme) OR a risk_reward-multiple target is hit OR the
  vol regime flips to non-low (risk-off exit, same convention as
  2026-09-03_bb_meanrev_qqq_volregime.py) OR a max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _low_vol_regime(close: pd.Series, vol_window: int, vol_lookback: int, vol_regime_ratio: float) -> pd.Series:
    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    return (realized_vol <= (vol_median * vol_regime_ratio)).fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    swing_lookback: int = 10,
    risk_reward: float = 2.0,
    max_hold_days: int = 10,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]

    low_vol_regime = _low_vol_regime(close, vol_window, vol_lookback, vol_regime_ratio)

    swing_low = low.rolling(swing_lookback).min().shift(1)
    sfp_confirmed = (low < swing_low) & (close > swing_low)
    sfp_confirmed = (sfp_confirmed & low_vol_regime).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_price = 0.0
    target_price = 0.0

    n = len(close)
    for i in range(n):
        if in_position:
            held = i - entry_idx
            c = close.iloc[i]
            if (
                c <= stop_price
                or c >= target_price
                or held >= max_hold_days
                or not bool(low_vol_regime.iloc[i])
            ):
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if i > 0 and bool(sfp_confirmed.iloc[i - 1]):
                in_position = True
                entry_idx = i
                entry_price = close.iloc[i]
                sweep_low = low.iloc[i - 1]
                stop_price = sweep_low
                risk = max(entry_price - stop_price, 1e-9)
                target_price = entry_price + risk_reward * risk
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
