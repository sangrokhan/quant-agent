"""Strategy: PPO + TRIX synchronized dual-confirmation crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-023):
Per Google AI-overview synthesis: a long entry requires BOTH the
Percentage Price Oscillator (PPO) crossing above its own EMA signal line
AND TRIX (triple-smoothed EMA rate of change) crossing above its own EMA
signal line, with the two crossovers occurring within a short
synchronization window (source suggests within 2 bars of each other) --
reducing whipsaw versus either single-oscillator crossover alone by
requiring cross-confirmation from two independently-constructed momentum
oscillators. This repo has 8 prior PPO entries and 15 prior TRIX entries
(including signal-line-crossover variants tested SEPARATELY for each, e.g.
PPO threshold/crossover variants and TRIX zero-line/signal-line/continuous-
sizing variants) but none combined both into a synchronized dual-
confirmation gate -- a genuinely new two-oscillator construction.

Signal logic
------------
- PPO[t] = 100 * (EMA(fast_span, close) - EMA(slow_span, close)) /
  EMA(slow_span, close); PPO_signal = EMA(ppo_signal_span, PPO).
- TRIX[t] = 1-period pct rate of change of a triple-smoothed EMA
  (EMA(EMA(EMA(close, trix_span)))); TRIX_signal = EMA(trix_signal_span,
  TRIX).
- Entry (long): PPO crosses above PPO_signal AND TRIX crosses above
  TRIX_signal, with the two cross events occurring within sync_window bars
  of each other (either order).
- Exit: EITHER oscillator crosses back below its own signal line (source's
  own stated "reverse signal" rule -- either indicator flipping is enough
  to exit), OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _ppo(close: pd.Series, fast_span: int, slow_span: int, signal_span: int):
    ema_fast = close.ewm(span=fast_span, adjust=False).mean()
    ema_slow = close.ewm(span=slow_span, adjust=False).mean()
    ppo = 100.0 * (ema_fast - ema_slow) / ema_slow
    ppo_signal = ppo.ewm(span=signal_span, adjust=False).mean()
    return ppo, ppo_signal


def _trix(close: pd.Series, trix_span: int, signal_span: int):
    ema1 = close.ewm(span=trix_span, adjust=False).mean()
    ema2 = ema1.ewm(span=trix_span, adjust=False).mean()
    ema3 = ema2.ewm(span=trix_span, adjust=False).mean()
    trix = 100.0 * ema3.pct_change()
    trix_signal = trix.ewm(span=signal_span, adjust=False).mean()
    return trix, trix_signal


def generate_signals(
    price_df: pd.DataFrame,
    ppo_fast: int = 12,
    ppo_slow: int = 26,
    ppo_signal_span: int = 9,
    trix_span: int = 14,
    trix_signal_span: int = 9,
    sync_window: int = 2,
    max_hold_days: int = 40,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a {0,leverage_cap} long/flat position series.

    ``leverage_cap`` scales exposure (default 1.0). Added for a potential
    crypto MDD leverage-cap-recalibration follow-up.
    """
    df = _prep(price_df)
    close = df["close"]

    ppo, ppo_sig = _ppo(close, ppo_fast, ppo_slow, ppo_signal_span)
    trix, trix_sig = _trix(close, trix_span, trix_signal_span)

    ppo_above = ppo > ppo_sig
    ppo_cross_up = ppo_above & (~ppo_above.shift(1).fillna(False))
    ppo_below = ppo < ppo_sig
    ppo_cross_down = ppo_below & (~ppo_below.shift(1).fillna(True))

    trix_above = trix > trix_sig
    trix_cross_up = trix_above & (~trix_above.shift(1).fillna(False))
    trix_below = trix < trix_sig
    trix_cross_down = trix_below & (~trix_below.shift(1).fillna(True))

    # Synchronized dual-confirmation: either cross-up event has the OTHER
    # oscillator's cross-up within +/- sync_window bars.
    ppo_cross_up_roll = ppo_cross_up.rolling(2 * sync_window + 1, center=True, min_periods=1).max().astype(bool)
    trix_cross_up_roll = trix_cross_up.rolling(2 * sync_window + 1, center=True, min_periods=1).max().astype(bool)
    entry = (ppo_cross_up & trix_cross_up_roll) | (trix_cross_up & ppo_cross_up_roll)

    exit_signal = ppo_cross_down | trix_cross_down

    position = pd.Series(0.0, index=close.index, dtype=float)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0.0
                continue
            position.iloc[i] = leverage_cap
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = leverage_cap
            else:
                position.iloc[i] = 0.0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
