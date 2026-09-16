"""Strategy: Pocket Pivot volume signature with inverse-vol position sizing
(rescue attempt for crypto's decisive MDD-only failure in the unsized base
version, 2026-09-17-012).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-013):
The base Pocket Pivot strategy (2026-09-17-012, source:
https://www.luxalgo.com/library/indicator/pocket-pivot/) showed ETH/USDT
passing Sharpe (1.204) and TC-survival (1.181) comfortably but decisively
failing max drawdown (0.352 vs 0.25); BTC/USDT similarly failed MDD (0.358)
with a near-miss Sharpe (0.977). This applies this repo's established
inverse-realized-volatility position-sizing overlay (same technique
validated twice already this cron trigger: 2026-09-17-009 HACO,
2026-09-17-010 Synthetic Oscillator) on top of the identical Pocket Pivot
signal, to test whether it rescues crypto's MDD the same way.

Signal logic
------------
- Identical Pocket Pivot entry/exit signal as 2026-09-17-012 (imported
  unmodified from that file).
- Position SIZE (not just 0/1) = target_vol / trailing realized_vol of the
  underlying, capped at [0, max_leverage], applied only on days the base
  signal is long (else 0).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (continuous [0, max_leverage] sizing)
    generate_returns(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import importlib.util
import os

import pandas as pd
import numpy as np

_BASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "2026-09-17_pocket_pivot_volume_signature.py")
_spec = importlib.util.spec_from_file_location("pocket_pivot_base_mod", _BASE_PATH)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    down_day_lookback: int = 10,
    fast_window: int = 10,
    slow_window: int = 50,
    support_proximity_pct: float = 0.02,
    max_hold_days: int = 15,
    target_vol: float = 0.15,
    vol_window: int = 20,
    max_leverage: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, max_leverage] sizing series."""
    df = _prep(price_df)
    base_position = _base.generate_signals(
        df, down_day_lookback=down_day_lookback, fast_window=fast_window,
        slow_window=slow_window, support_proximity_pct=support_proximity_pct,
        max_hold_days=max_hold_days,
    )
    close = df["close"]
    daily_log_ret = np.log(close / close.shift(1))
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    scale = (target_vol / realized_vol).clip(upper=max_leverage).fillna(0.0)
    scale = scale.clip(lower=0.0)
    sized_position = base_position * scale
    return sized_position.reindex(df.index).fillna(0.0)


def generate_returns(
    price_df: pd.DataFrame,
    down_day_lookback: int = 10,
    fast_window: int = 10,
    slow_window: int = 50,
    support_proximity_pct: float = 0.02,
    max_hold_days: int = 15,
    target_vol: float = 0.15,
    vol_window: int = 20,
    max_leverage: float = 1.0,
) -> pd.Series:
    """Return daily strategy returns (sized position-weighted, no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        df, down_day_lookback=down_day_lookback, fast_window=fast_window,
        slow_window=slow_window, support_proximity_pct=support_proximity_pct,
        max_hold_days=max_hold_days, target_vol=target_vol, vol_window=vol_window,
        max_leverage=max_leverage,
    )
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
