"""Strategy: monthly "buy-the-dip" -- long for one month after a sharp
trailing-month drawdown, per Javier Estrada's BTD threshold sweep.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Source: CXO Advisory's summary of Javier Estrada's May 2026 paper "Buy the
Dip? Not So Fast" (https://www.cxoadvisory.com/technical-trading/to-buy-or-not-to-buy-the-dip/).
The paper's own disclosed design: after a month with a negative market
return below a dip threshold (source tests -3%, -6%, -9%, -12%, -15%),
shift capital from a bond allocation into buying the dip; the CXO summary's
verdict itself is paywalled, so this iteration does NOT assume the source's
finding is positive -- it independently tests the mechanical rule using
this repo's own grid/validator pipeline rather than taking the paper's word
for it, per RESEARCH_LOOP's "ground hypotheses in what was read, verify
independently" principle.

Single-asset daily-bar adaptation (this repo's grid tester trades one
symbol long/flat, not a 2-asset stock/bond capital-shift):
- Compute the trailing 21-trading-day (~1 calendar month) return.
- On any day where that trailing-month return crosses below
  -dip_threshold (e.g. -0.06 for the paper's -6% dip bucket), go long
  for the following hold_days trading days (source's own "for the next
  period" semantics, here a fixed ~1-month hold rather than open-ended).
  While already in a triggered hold, do not re-trigger (avoid overlapping
  stacked signals -- this is a discrete event-driven long, not a
  continuous state).
- Otherwise flat.

Distinct from every other repo strategy: this is the first strategy keyed
on a TRAILING ~1-MONTH (21-day) return threshold specifically (not RSI/BB/
oscillator dips, not single/multi *daily* down-close streaks like
2026-09-04's "MDD multiple days down", and not the accepted
formation-price stop-loss/6-month-momentum crash-protection overlay
2026-09-08-178, which triggers on stock-level DRAWDOWN FROM PORTFOLIO
FORMATION, not a fixed trailing-window market return).

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def generate_signals(
    price_df: pd.DataFrame,
    lookback_days: int = 21,
    dip_threshold: float = 0.06,
    hold_days: int = 21,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    trailing_return = close.pct_change(lookback_days)
    # Trigger known only as of yesterday's close (no lookahead into today).
    trigger_raw = (trailing_return.shift(1) <= -abs(dip_threshold)).fillna(False)

    n = len(df)
    position = np.zeros(n, dtype=int)
    trig = trigger_raw.to_numpy()

    hold_remaining = 0
    for i in range(n):
        if hold_remaining > 0:
            position[i] = 1
            hold_remaining -= 1
        elif trig[i]:
            position[i] = 1
            hold_remaining = hold_days - 1

    signal = pd.Series(position, index=df.index, name="position")
    return signal


def generate_returns(
    price_df: pd.DataFrame,
    lookback_days: int = 21,
    dip_threshold: float = 0.06,
    hold_days: int = 21,
) -> pd.Series:
    df = _prep(price_df)
    signal = generate_signals(
        df, lookback_days=lookback_days, dip_threshold=dip_threshold, hold_days=hold_days
    )
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = signal.shift(0) * daily_returns  # signal already lagged inside generate_signals
    strat_returns = strat_returns.fillna(0.0)
    strat_returns.name = "returns"
    return strat_returns
