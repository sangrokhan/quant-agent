"""Strategy: HYG Weak-Monday Overnight Reversal (Monday close -> Tuesday open only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-XXX):
Per Quantpedia's "Overnight Reversal Effects in the High-Yield Market"
(https://quantpedia.com/overnight-reversal-effects-in-the-high-yield-market/,
Cyril Dujava, Aug 2024, read via browser_exec since web_extract's DDGS
backend cannot extract page content): HYG (iShares iBoxx $ High Yield
Corporate Bond ETF) shows a systematic overnight (close-to-open) return
premium concentrated in the Monday-close->Tuesday-open and
Tuesday-close->Wednesday-open sessions, with the effect strongest and most
"persistent and apparent" specifically in the Monday->Tuesday overnight
session WHEN Friday's close-to-Monday's-close return was negative ("a weak
Monday, when the close is significantly lower than Friday's") -- the
source's own name for this is "Turnaround Tuesday" applied to the
overnight leg specifically, not the full trading day.

This is distinct from the already-tested 2026-09-20-059 (HYG Turnaround
Tuesday, Monday close->Tuesday CLOSE full-day hold, rejected: unconditional
Sharpe 0.761, Monday-down-conditional gate makes it WORSE at 0.575).
2026-09-20-059 realizes the FULL Tuesday trading session (Monday close
through Tuesday close, including Tuesday's intraday move); this strategy
instead isolates ONLY the overnight leg (Monday close -> Tuesday OPEN),
which per the source's own chart-based finding is where HYG's edge is
concentrated (the article shows overnight sessions "fare the best" while
"daily sessions ... hurt and do not contribute ... at all"). Different
return-generation mechanism, same underlying calendar/conditional trigger.

Signal logic
------------
- gate_weekday (default 0 = Monday): the day whose own close-to-close
  return we condition on.
- daily_ret(t) = close(t)/close(t-1) - 1
- trigger(t) = True iff weekday(t) == gate_weekday AND daily_ret(t) <
  down_thresh (a "weak" gate-day close).
- Position: hold ONLY overnight from trigger day t's close through t+1's
  open (t+1 is expected to be the next trading day, e.g. Tuesday if HYG
  trades every weekday with no gate_weekday holiday gaps). Flat all other
  times, including flat for the entire Tuesday trading session itself.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1})
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    gate_weekday: int = 0,
    down_thresh: float = 0.0,
) -> pd.Series:
    """Return a {0,1} position series.

    position.iloc[i] == 1 means "holding the overnight position entered
    at the close of the PRIOR bar (i-1), exiting at this bar's open" --
    i.e. the trigger fired on bar i-1.
    """
    df = _prep(price_df)
    close = df["close"]

    daily_ret = close.pct_change()
    weekday = pd.Series(close.index).dt.weekday
    weekday.index = close.index

    trigger = (weekday == gate_weekday) & (daily_ret < down_thresh)
    trigger = trigger.fillna(False)

    position = trigger.shift(1).fillna(False).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    gate_weekday: int = 0,
    down_thresh: float = 0.0,
) -> pd.Series:
    """Overnight (close[i-1] -> open[i]) returns, applied only on days
    where `generate_signals` indicates an active overnight position.
    """
    df = _prep(price_df)
    open_ = df["open"]
    close = df["close"]

    position = generate_signals(price_df, gate_weekday=gate_weekday, down_thresh=down_thresh)
    overnight_ret = (open_ / close.shift(1) - 1.0).fillna(0.0)
    strategy_ret = position * overnight_ret
    return strategy_ret.fillna(0.0)
