"""Strategy: Ensemble majority-vote of 3 near-miss single-signal strategies
(TRIX signal-line crossover, ADX/DMI DI+/DI- crossover, RVI signal-line
crossover) -- rescue attempt for a pattern this KB flagged explicitly.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-044):
Three independent strategies tested in the same prior cron trigger all
produced SPY near-misses in the 0.92-0.98 full-sample Sharpe range, each
sharing the "oscillator crosses its own signal line, gated by a static
trend filter" shape but using DIFFERENT underlying oscillators:
  - TRIX(14)/signal(9) + 50/200 EMA regime (2026-09-23-031, Sharpe 0.983)
  - ADX/DMI DI+/DI- crossover + ADX>=25 gate (2026-09-23-033, Sharpe 0.929)
  - RVI(10)/signal + 200 SMA trend filter (2026-09-23-034, Sharpe 0.931)
That entry's own notes explicitly proposed testing "whether an ensemble/
majority-vote combination of these 3 near-miss signals clears 1.0 where
none does alone" -- this strategy implements exactly that test: at each
bar, each of the 3 underlying strategies independently computes its own
{0,1} position (calling their own generate_signals functions directly, no
reimplementation of their internal logic), and the ensemble is long only
when at least `min_votes` (default 2, i.e. majority) of the 3 are long.
The economic rationale: if the three oscillators are picking up correlated-
but-imperfect signals of the same underlying trend, requiring agreement
should filter out each individual oscillator's idiosyncratic false signals
while keeping true trend periods (where all 3 tend to agree) -- at the
cost of fewer total trades.

Signal logic
------------
- Compute TRIX, ADX-DI, and RVI position series independently (their own
  default parameters, unchanged from their original strategy files).
- Ensemble position = 1 iff sum(the three {0,1} series) >= min_votes.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import importlib.util
import os

import pandas as pd

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_module(filename: str, modname: str):
    spec = importlib.util.spec_from_file_location(modname, os.path.join(_THIS_DIR, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_trix_mod = _load_module("2026-09-23_trix_signal_cross_ema_regime.py", "_trix_near_miss")
_adx_mod = _load_module("2026-09-23_adx_di_crossover_atr_risk.py", "_adx_near_miss")
_rvi_mod = _load_module("2026-09-23_rvi_signal_cross_trend_filter.py", "_rvi_near_miss")


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    min_votes: int = 2,
    trix_window: int = 14,
    trix_signal_window: int = 9,
    trix_fast_ema: int = 50,
    trix_slow_ema: int = 200,
    adx_window: int = 14,
    adx_entry_threshold: float = 25.0,
    adx_exit_threshold: float = 20.0,
    atr_stop_mult: float = 1.5,
    reward_risk: float = 2.0,
    rvi_window: int = 10,
    rvi_trend_sma_window: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series (majority vote of 3 signals)."""
    df = _prep(price_df)

    trix_pos = _trix_mod.generate_signals(
        df,
        trix_window=trix_window,
        signal_window=trix_signal_window,
        fast_ema=trix_fast_ema,
        slow_ema=trix_slow_ema,
    )
    adx_pos = _adx_mod.generate_signals(
        df,
        adx_window=adx_window,
        adx_entry_threshold=adx_entry_threshold,
        adx_exit_threshold=adx_exit_threshold,
        atr_stop_mult=atr_stop_mult,
        reward_risk=reward_risk,
    )
    rvi_pos = _rvi_mod.generate_signals(
        df,
        rvi_window=rvi_window,
        trend_sma_window=rvi_trend_sma_window,
    )

    votes = trix_pos.reindex(df.index).fillna(0) + adx_pos.reindex(df.index).fillna(0) + rvi_pos.reindex(
        df.index
    ).fillna(0)
    ensemble = (votes >= min_votes).astype(int)
    return ensemble


def generate_returns(
    price_df: pd.DataFrame,
    min_votes: int = 2,
    trix_window: int = 14,
    trix_signal_window: int = 9,
    trix_fast_ema: int = 50,
    trix_slow_ema: int = 200,
    adx_window: int = 14,
    adx_entry_threshold: float = 25.0,
    adx_exit_threshold: float = 20.0,
    atr_stop_mult: float = 1.5,
    reward_risk: float = 2.0,
    rvi_window: int = 10,
    rvi_trend_sma_window: int = 200,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        min_votes=min_votes,
        trix_window=trix_window,
        trix_signal_window=trix_signal_window,
        trix_fast_ema=trix_fast_ema,
        trix_slow_ema=trix_slow_ema,
        adx_window=adx_window,
        adx_entry_threshold=adx_entry_threshold,
        adx_exit_threshold=adx_exit_threshold,
        atr_stop_mult=atr_stop_mult,
        reward_risk=reward_risk,
        rvi_window=rvi_window,
        rvi_trend_sma_window=rvi_trend_sma_window,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = (position.shift(1).fillna(0) * daily_ret).fillna(0.0)
    return strat_ret
