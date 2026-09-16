"""Strategy: HACO regime-flip with an inverse-volatility position-sizing
overlay (direct follow-up to 2026-09-16-118's QQQ near-miss).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-009):
The prior HACO regime-flip strategy (2026-09-16-118, Sylvain Vervoort's
zero-lag-TEMA Heikin-Ashi oscillator, source:
https://www.tradingview.com/script/UyhY8FuQ-Vervoort-Heiken-Ashi-Candlestick-Oscillator/)
was accepted for SPY but explicitly REJECTED for QQQ as a near-miss: "QQQ:
near-miss MDD (0.283 vs 0.25 threshold), everything else passes cleanly --
plausible vol-target rescue candidate for a future iteration" (per that
entry's own `rejection_reason`).

This strategy tests exactly that suggested rescue: keep the identical HACO
regime-flip entry/exit logic unchanged, but scale the position size
inversely to trailing realized volatility (target_vol / realized_vol,
capped at max_leverage) instead of a flat binary 0/1 long/flat position.
This is this repo's standard vol-targeting overlay pattern (see e.g.
strategies/*_voltarget_buffer.py files), applied here specifically to
address the QQQ MDD near-miss recorded in 2026-09-16-118's notes -- not an
invented recombination, but the direct next step the prior entry's own log
called for.

Signal logic
------------
- Identical HACO oscillator computation and long/flat regime signal as
  2026-09-16-118 (imported unmodified from that file to guarantee byte-for-
  byte equivalence of the underlying regime detector).
- Position SIZE (not just 0/1) = target_vol / trailing realized_vol of the
  underlying, capped at [0, max_leverage], applied only on days the base
  HACO regime signal is long (else 0).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (continuous [0, max_leverage] sizing)
    generate_returns(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import importlib.util
import os

import pandas as pd
import numpy as np

_HACO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "2026-09-16_haco_zltema_regime.py")
_spec = importlib.util.spec_from_file_location("haco_base_mod", _HACO_PATH)
_haco_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_haco_base)


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    avg_up: int = 34,
    avg_dn: int = 34,
    keep_body_ratio: float = 0.35,
    max_hold_days: int = 60,
    target_vol: float = 0.15,
    vol_window: int = 20,
    max_leverage: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, max_leverage] sizing series."""
    df = _prep(price_df)
    base_position = _haco_base.generate_signals(
        df, avg_up=avg_up, avg_dn=avg_dn, keep_body_ratio=keep_body_ratio, max_hold_days=max_hold_days
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
    avg_up: int = 34,
    avg_dn: int = 34,
    keep_body_ratio: float = 0.35,
    max_hold_days: int = 60,
    target_vol: float = 0.15,
    vol_window: int = 20,
    max_leverage: float = 1.0,
) -> pd.Series:
    """Return daily strategy returns (sized position-weighted, no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        df, avg_up=avg_up, avg_dn=avg_dn, keep_body_ratio=keep_body_ratio,
        max_hold_days=max_hold_days, target_vol=target_vol, vol_window=vol_window,
        max_leverage=max_leverage,
    )
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
