"""Strategy: Majority-vote ensemble of three independent SPY near-miss
oscillator-crossover-plus-trend-filter signals from this cron trigger
(TRIX signal-line, ADX/DMI DI+/DI-, RVI signal-line), each of which
individually near-missed the Sharpe >= 1.0 threshold (0.983, 0.929, 0.931
respectively) on SPY.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-23-035):
Direct follow-up testing the pattern flagged in this cron trigger's own
2026-09-23-034 (RVI) notes: three independently-sourced oscillator-
crossover-plus-trend-filter strategies (2026-09-23-031 TRIX, 2026-09-23-033
ADX-DI, 2026-09-23-034 RVI) all near-missed Sharpe 1.0 on SPY specifically,
in a tight 0.929-0.983 range. Rather than tuning any ONE further, this
iteration tests whether requiring AT LEAST 2 of the 3 signals to agree
(majority vote) reduces whipsaw/false-signal noise enough to push the
combined signal over the threshold, since each individual signal's
"failure mode" is presumably different specific whipsaw periods that a
majority-vote filter could screen out. No new external source read this
iteration -- a pure internal-KB follow-up on three already-sourced
hypotheses (each with its own logged source URL).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importlib.util
import pandas as pd


def _load_strat(filename: str):
    spec = importlib.util.spec_from_file_location(
        filename, os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_trix = _load_strat("2026-09-23_trix_signal_cross_ema_regime.py")
_adx = _load_strat("2026-09-23_adx_di_crossover_atr_risk.py")
_rvi = _load_strat("2026-09-23_rvi_signal_cross_trend_filter.py")


def generate_signals(
    price_df: pd.DataFrame,
    min_votes: int = 2,
) -> pd.Series:
    """Return a {0,1} long/flat position series based on majority vote."""
    pos_trix = _trix.generate_signals(price_df, trix_window=14, signal_window=12, fast_ema=50, slow_ema=200)
    pos_adx = _adx.generate_signals(price_df, adx_entry_threshold=25, adx_exit_threshold=20, atr_stop_mult=1.5, reward_risk=2.0)
    pos_rvi = _rvi.generate_signals(price_df, rvi_window=14, trend_sma_window=200)

    votes = pos_trix.reindex(price_df.index if "timestamp" not in price_df.columns else None)
    # Align all three on a common index (they should already share price_df's index)
    df_votes = pd.concat([pos_trix, pos_adx, pos_rvi], axis=1).fillna(0)
    vote_sum = df_votes.sum(axis=1)
    position = (vote_sum >= min_votes).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    min_votes: int = 2,
) -> pd.Series:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    close = df["close"]
    position = generate_signals(price_df, min_votes=min_votes)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = (position.shift(1).fillna(0) * daily_ret).fillna(0.0)
    return strat_ret
