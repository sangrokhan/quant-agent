"""Strategy: 39-period Slow Stochastic %K 50-line cross, OBV-confirmed,
leverage-cap-aware crypto rescue of 2026-09-18-106.

Hypothesis (see knowledge_base/strategies_log.jsonl for this id):
Direct rescue of this same cron trigger's prior entry (2026-09-18-106,
strategies/2026-09-18_stoch39_obv_confirm.py): the underlying signal (long
whenever 39-period Stochastic %K > 50 AND OBV > OBV's own 30-day SMA)
directionally generalizes to crypto (BTC/USDT Sharpe 1.34, ETH/USDT Sharpe
1.23, both with near-perfect walk-forward and low parameter sensitivity),
but the FULL-EXPOSURE (0/1 binary) version decisively fails max drawdown on
both crypto symbols (46.5%/58.7% vs 25% cap) -- the strategy stays long
through crypto's much larger multi-month drawdown episodes since the
signal's exit condition reacts comparatively slowly to sudden severe
reversals at crypto's scale of moves.

Since Sharpe/parameter-sensitivity/walk-forward are all leverage-invariant
(scaling every period's return by a constant multiplier doesn't change the
Sharpe ratio, sign of walk-forward-slice returns, or relative parameter
sensitivity) while max drawdown scales roughly linearly with exposure, this
applies this repo's standard leverage-cap-aware rescue pattern (see e.g.
strategies/2026-09-14_nvi_sizing_sma_trend_crypto_lev.py and dozens of
other `*_crypto_lev.py` files in this repo): the SAME binary signal, scaled
down to a fixed leverage_cap exposure level (found via a direct MDD-vs-
leverage scan) instead of full 1.0x exposure, so the equity-cliff-avoiding
directional signal is preserved while keeping crypto's larger absolute
moves within the risk budget.

This is NOT a modification of the underlying signal logic at all (identical
Stochastic+OBV condition to strategies/2026-09-18_stoch39_obv_confirm.py) --
purely a position-sizing/leverage-cap wrapper, logged as a separate entry
per this repo's convention for crypto-rescue leverage-cap sub-iterations.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series
    generate_returns(price_df, **params) -> pd.Series
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


def _stochastic_k(df: pd.DataFrame, window: int) -> pd.Series:
    low_min = df["low"].rolling(window).min()
    high_max = df["high"].rolling(window).max()
    denom = (high_max - low_min).replace(0, np.nan)
    k = 100.0 * (df["close"] - low_min) / denom
    return k.fillna(50.0)


def _obv(df: pd.DataFrame) -> pd.Series:
    direction = np.sign(df["close"].diff().fillna(0.0))
    return (direction * df["volume"]).cumsum()


def _core_binary(
    price_df: pd.DataFrame,
    stoch_window: int,
    obv_sma_window: int,
    k_midline: float,
) -> pd.Series:
    df = _prep(price_df)
    k = _stochastic_k(df, stoch_window)
    obv = _obv(df)
    obv_sma = obv.rolling(obv_sma_window).mean()
    bullish_momentum = k > k_midline
    bullish_volume = obv > obv_sma
    return (bullish_momentum & bullish_volume).astype(int)


def generate_signals(
    price_df: pd.DataFrame,
    stoch_window: int = 39,
    obv_sma_window: int = 20,
    k_midline: float = 50.0,
    leverage_cap: float = 0.4,
) -> pd.Series:
    """Binary {0,1} position indicator (the leverage cap is applied only in
    generate_returns, not to this indicator series, since validators that
    need a {0,1} series -- e.g. paper_trading -- expect a plain long/flat
    flag rather than a fractional exposure)."""
    return _core_binary(price_df, stoch_window, obv_sma_window, k_midline)


def generate_returns(
    price_df: pd.DataFrame,
    stoch_window: int = 39,
    obv_sma_window: int = 20,
    k_midline: float = 50.0,
    leverage_cap: float = 0.4,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = _core_binary(df, stoch_window, obv_sma_window, k_midline)
    daily_ret = close.pct_change().fillna(0.0)
    return leverage_cap * daily_ret * position.shift(1).fillna(0)
