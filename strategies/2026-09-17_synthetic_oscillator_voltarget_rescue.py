"""Strategy: Ehlers Synthetic Oscillator with inverse-vol position sizing
(direct follow-up to 2026-09-12-178's QQQ/SPY near-misses).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-010):
The prior Synthetic Oscillator strategy (2026-09-12-178, John F. Ehlers'
April 2026 TASC "Avoiding Whipsaw Trades", source:
https://www.tradingview.com/script/we9AMcvE-TASC-2026-04-A-Synthetic-Oscillator/)
was rejected on BOTH equity symbols, but each failed only ONE validator by a
narrow margin: "QQQ (hann_len=12/upper_bound=48) fails max drawdown (0.263 >
0.25 threshold) despite Sharpe 1.218/TC/walk-forward/param-sensitivity all
passing; SPY (hann_len=12/upper_bound=60) fails parameter sensitivity
(relative std 0.581 > 0.5) despite Sharpe 1.155/MDD/TC/walk-forward all
passing" (per that entry's own `rejection_reason`).

This repo has an established pattern (see 2026-09-17-009, this same cron
trigger) for exactly this situation: apply an inverse-realized-volatility
position-sizing overlay on top of an otherwise-unchanged binary regime
signal to directly address an MDD near-miss. Since QQQ's near-miss was
specifically an MDD failure (not Sharpe/TC/walk-forward/sensitivity), this
is the natural next test -- not an invented recombination, but a direct,
source-grounded rescue attempt building on this repo's own established
technique and this signal's own documented near-miss.

Signal logic
------------
- Identical Synthetic Oscillator computation and long/flat zero-cross
  signal as 2026-09-12-178 (imported unmodified from that file).
- Position SIZE (not just 0/1) = target_vol / trailing realized_vol of the
  underlying, capped at [0, max_leverage], applied only on days the base
  oscillator signal is long (else 0).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (continuous [0, max_leverage] sizing)
    generate_returns(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import importlib.util
import os

import pandas as pd
import numpy as np

_BASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "2026-09-12_ehlers_synthetic_oscillator.py")
_spec = importlib.util.spec_from_file_location("synth_osc_base_mod", _BASE_PATH)
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
    hann_len: int = 12,
    lower_bound: int = 10,
    upper_bound: int = 48,
    target_vol: float = 0.15,
    vol_window: int = 20,
    max_leverage: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, max_leverage] sizing series."""
    df = _prep(price_df)
    base_position = _base.generate_signals(
        df, hann_len=hann_len, lower_bound=lower_bound, upper_bound=upper_bound
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
    hann_len: int = 12,
    lower_bound: int = 10,
    upper_bound: int = 48,
    target_vol: float = 0.15,
    vol_window: int = 20,
    max_leverage: float = 1.0,
) -> pd.Series:
    """Return daily strategy returns (sized position-weighted, no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        df, hann_len=hann_len, lower_bound=lower_bound, upper_bound=upper_bound,
        target_vol=target_vol, vol_window=vol_window, max_leverage=max_leverage,
    )
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
