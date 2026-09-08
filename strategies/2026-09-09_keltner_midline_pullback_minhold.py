"""Strategy: Keltner Channel middle-line pullback + min-hold-days gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-030):
Direct follow-up to near-miss 2026-09-06-136 (Keltner Channel middle-line
pullback trend-continuation, per ThinkMarkets: "buying dips to the middle
line in an uptrend"). That strategy's own notes flagged the exact failure
mode: raw Sharpe was a near-miss (0.965 SPY) and parameter-sensitivity
passed cleanly (0.309), but it was decisively rejected on
transaction-cost-survival because 442 trades over 7.7yr let 10bps/trade
costs flip net Sharpe negative (-0.089 vs the 0.5 threshold) -- a pure
overtrading problem, not a signal-quality problem. The notes explicitly
recommended: "a future revisit should add a re-entry cooldown or much
longer hold period to reduce trade count before transaction costs are
re-tested."

This iteration applies the SAME min_hold_days fix pattern already validated
3x elsewhere in this repo (Klinger Volume Oscillator 2026-09-04-085, ZLEMA
2026-09-06-171, Accelerator Oscillator 2026-09-06-174): add an explicit
min_hold_days gate that suppresses ALL exit conditions (basis-break,
trend-break, AND the original bounce-confirm re-entry check) for the first
N days after entry, cutting trade COUNT without touching the underlying
entry/exit signal logic itself. If this reduces trade count enough that
transaction costs no longer dominate, the near-miss raw Sharpe should
translate into a passing net-of-cost Sharpe.

Signal logic (identical entry/exit conditions to 2026-09-06-136, plus the
min_hold_days gate)
------------------------------------------------------------------------
- Keltner basis = EMA(kc_window); bands = basis +/- kc_mult * ATR(kc_window)
  (kc_mult retained for interface parity with the predecessor, unused in
  the middle-line-only entry/exit logic, matching the original file).
- Uptrend gate: close > SMA(trend_window).
- Entry: close pulls back to/below the middle basis line (close <= basis)
  while in the uptrend gate, then the NEXT bar's close recovers back above
  the basis line (bounce confirmation).
- Exit: only evaluated once held >= min_hold_days: close crosses back
  below the basis line, the uptrend gate breaks, or a max_hold_days
  time-stop is reached.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series {0,1} long/flat
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window, min_periods=window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    kc_window: int = 20,
    kc_mult: float = 1.5,
    trend_window: int = 100,
    max_hold_days: int = 15,
    min_hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    basis = close.ewm(span=kc_window, min_periods=kc_window, adjust=False).mean()
    trend_sma = close.rolling(trend_window, min_periods=trend_window).mean()

    uptrend = close > trend_sma
    touched_basis = close <= basis
    bounce_confirm = (close > basis) & touched_basis.shift(1).fillna(False) & uptrend.shift(1).fillna(False)

    idx = df.index
    n = len(idx)
    pos = pd.Series(0, index=idx, dtype=int)
    in_pos = False
    entry_idx = None

    for i in range(n):
        if in_pos:
            days_held = i - entry_idx
            if days_held < min_hold_days:
                # Suppress all exit checks (and re-entry scanning) while
                # inside the minimum hold window -- this is the trade-count
                # reduction fix.
                pos.iloc[i] = 1
                continue
            hit_time = days_held >= max_hold_days
            hit_basis_break = close.iloc[i] < basis.iloc[i]
            hit_trend_break = not bool(uptrend.iloc[i])
            if hit_time or hit_basis_break or hit_trend_break:
                in_pos = False
            else:
                pos.iloc[i] = 1
                continue
        else:
            if bool(bounce_confirm.iloc[i]) and bool(uptrend.iloc[i]):
                in_pos = True
                entry_idx = i
                pos.iloc[i] = 1

    return pos


def generate_returns(
    price_df: pd.DataFrame,
    kc_window: int = 20,
    kc_mult: float = 1.5,
    trend_window: int = 100,
    max_hold_days: int = 15,
    min_hold_days: int = 5,
) -> pd.Series:
    """Daily strategy returns (no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]
    pos = generate_signals(
        price_df,
        kc_window=kc_window,
        kc_mult=kc_mult,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
        min_hold_days=min_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = pos.shift(1).fillna(0) * daily_ret
    return strat_ret
