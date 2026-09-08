"""Strategy: Third-Friday Price Spike (Derivative Payoff Bias / Charm-driven
overnight drift into monthly options expiration).

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD):
Per Baltussen, Terstegge & Whelan, "The Derivative Payoff Bias" (summarized
at https://www.quantitativo.com/p/the-derivative-payoff-bias): many S&P 500
index options/futures settle on the Special Opening Quotation (SOQ) --
the opening price on the 3rd Friday of each month. Since ~2003, dealer
Charm-hedging (delta's rate of change over time, intensifying as expiration
approaches) creates systematic overnight buying pressure into that SOQ
window, producing a "Third Friday Price Spike" (3FPS): prices drift up
overnight from Thursday's close into Friday's open, then partially reverse
intraday. The source's own exploitation rule: go long at Thursday close,
reverse to short at Friday open, close the short before Friday noon. This
repo's daily-bar-only loaders can't express an intraday short-before-noon
leg, so this adapts the LONG overnight leg only (Thursday close -> Friday
open captures the drift; the reversal leg is dropped since intraday data
isn't available): long-only overnight hold entered at Thursday's close,
exited at Friday's open, ONLY during 3rd-Friday-of-month
(monthly-options-expiration) weeks -- flat all other days. This is
distinct from the already-rejected monthly OPEX-week strategy
(2026-09-06-149, holds Monday open through Friday close, no overnight-only
mechanic) and Triple Witching (2026-09-06-178, holds Monday open through
Thursday close) -- this is the first strategy in this repo to target the
specific Thursday-close-to-Friday-open overnight window tied to the SOQ
settlement mechanism itself.

Signal logic
------------
- Identify each month's 3rd Friday (the standard monthly equity/index
  options expiration date).
- Position[t] = 1 (hold overnight into day t's open, entered at day t-1's
  close) iff day t IS that month's 3rd Friday; else 0.
- Overnight return for day t = open[t] / close[t-1] - 1, applied only on
  those qualifying 3rd-Friday bars.
- No intraday exposure at all (mirrors this repo's other overnight-hold
  strategies' structure, e.g. 2026-09-08-053).

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _is_third_friday(index: pd.DatetimeIndex) -> pd.Series:
    """True for each bar that is the 3rd Friday of its month (per calendar
    date, not trading-day count) -- the standard monthly options-expiration
    date, regardless of whether the underlying trading calendar happens to
    have a session that day (weekday check on the actual calendar date)."""
    is_friday = index.weekday == 4
    day_of_month = index.day
    # 3rd Friday falls on calendar day 15-21 inclusive.
    is_third_week = (day_of_month >= 15) & (day_of_month <= 21)
    return pd.Series(is_friday & is_third_week, index=index)


def generate_signals(
    price_df: pd.DataFrame,
    week_offset: int = 0,
) -> pd.Series:
    """Return a {0,1} series: 1 = holding overnight into this bar's open.

    `week_offset` (calendar days) allows a small robustness sweep around the
    exact 3rd-Friday date (e.g. testing a 1-day-early/late variant to check
    the signal isn't a knife-edge artifact of the exact SOQ date).
    """
    df = _prep(price_df)
    idx = df.index

    if week_offset != 0:
        shifted_idx = idx + pd.Timedelta(days=week_offset)
        is_target = _is_third_friday(shifted_idx)
        is_target.index = idx
    else:
        is_target = _is_third_friday(idx)

    position = is_target.astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Overnight-only daily returns: open[t]/close[t-1] - 1, gated to 3rd-Friday bars."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]

    position = generate_signals(price_df, **kwargs)
    overnight_ret = (open_ / close.shift(1) - 1.0).fillna(0.0)
    strategy_ret = position * overnight_ret
    return strategy_ret
