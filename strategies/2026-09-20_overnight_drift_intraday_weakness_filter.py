"""Strategy: Overnight-drift reversal, filtered by trailing intraday weakness.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-XXX):
Per WOLFX Research's "Overnight Drift Reversal" whitepaper
(https://wolfx.trade/whitepaper/overnight-drift, citing Lou/Polk/Skouras
2019 JFE and Bogousslavsky 2021 JFE academic findings), equity index
overnight returns (close-to-next-open) are on average positive while
intraday returns (open-to-close) are roughly flat/slightly negative
("the intraday tug of war"). The source's own disclosed, fully-mechanical
filter: only take the overnight long when the sum of the PRIOR 5
sessions' intraday log returns (log(close/open) each day) is negative
-- i.e. only harvest the overnight-drift premium on days following a
stretch where intraday holders have been "beaten up", which the source
claims concentrates the premium (their own head-to-head test: filtered
variant Sharpe 1.229 vs. unfiltered variant Sharpe 0.479 on their walk-
forward slice). Enter long at today's close, exit at tomorrow's open;
otherwise flat (cash) intraday.

This differs from every existing overnight-holding strategy already in
this repo's knowledge base: 2026-09-17-007 (5-Day-Low-OPEN trigger +
bullish intraday CLOSE confirmation, from quantifiedstrategies.com) and
2026-09-18-098/135 (N-consecutive-DOWN-CLOSE streak trigger, no intraday-
return-sum construction at all). This strategy's trigger is instead the
rolling SUM of trailing N-day intraday (open-to-close) log returns
crossing negative -- a distinct, source-disclosed numeric filter not
previously tested here.

Signal logic
------------
- intraday_log_ret(t) = log(close(t) / open(t))
- filter(t) = sum(intraday_log_ret(t-lag_window+1) .. intraday_log_ret(t))
  (trailing lag_window-day sum, default 5, per source)
- Enter long at close(t) whenever filter(t) < 0.
- Exit at open(t+1) (single-session overnight hold; approximated here as
  the strategy's daily return series being the overnight return
  close(t)->open(t+1) attributed to day t+1, flat otherwise, since this
  repo's generate_returns contract returns one daily-frequency return
  series rather than an explicit MOC/MOO fill schedule).
- No leverage, no shorting; long-only single-instrument as required by
  SAFETY.md.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
        Both take an OHLCV price_df (needs open AND close columns --
        this strategy is one of the few in this repo that uses the
        open column directly rather than just close).
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


def _filter_series(price_df: pd.DataFrame, lag_window: int) -> pd.Series:
    df = _prep(price_df)
    intraday_log_ret = np.log(df["close"] / df["open"])
    filt = intraday_log_ret.rolling(lag_window).sum()
    return filt


def generate_signals(
    price_df: pd.DataFrame,
    lag_window: int = 5,
) -> pd.Series:
    """Return a {0,1} position series: 1 on days we hold the overnight
    position INTO the close (i.e. position.iloc[t]==1 means "enter at
    close(t), exposed overnight t->t+1"). This intentionally does NOT
    represent intraday exposure -- see generate_returns for how the
    overnight-only P&L is derived from this trigger series.
    """
    filt = _filter_series(price_df, lag_window)
    trigger = (filt < 0).fillna(False).astype(int)
    return trigger


def generate_returns(
    price_df: pd.DataFrame,
    lag_window: int = 5,
) -> pd.Series:
    """Return the strategy's daily return series.

    Each day's return is the OVERNIGHT return realized THAT day (i.e.
    close(t-1)->open(t)), included only if the trigger fired at close
    of day t-1 (filter(t-1) < 0). Non-overnight (intraday) days are 0
    exposure by construction (cash), matching the source's exact rule.
    """
    df = _prep(price_df)
    trigger = generate_signals(df, lag_window=lag_window)

    open_ = df["open"]
    close = df["close"]
    overnight_ret = (open_ / close.shift(1)) - 1.0

    # trigger.shift(1): the decision to hold overnight into day t was
    # made at close of day t-1 based on filter(t-1); the P&L for that
    # decision is realized as day t's overnight_ret.
    position_active = trigger.shift(1).fillna(0)
    strat_ret = overnight_ret * position_active
    strat_ret = strat_ret.fillna(0.0)
    return strat_ret
