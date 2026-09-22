"""Strategy: Buy Every (Modest) Open Down (same-day open-to-close reversal).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-122):
Per QuantifiedStrategies.com's "Buy Every Open Down Trading Strategy"
(https://www.quantifiedstrategies.com/buy-every-open-down/, accessed
2026-09-22 via browser_exec after web_search DDGS backend returned only
snippets; this article's rule text was NOT paywalled), the disclosed rule
(originally tested on SPY, Jan 2010-Jun 2012) is:

    - If today's open is below yesterday's close (an "open down") but not
      TOO far down (source's stated cutoff: don't buy if the open-down
      magnitude exceeds ~0.45-0.5%), go long at the open.
    - Exit at the close (same trading day -- an intraday hold, no overnight
      exposure).
    - Source's own improvement: gating the long entry additionally on
      "the day before was itself a down day" raised the average per-trade
      gain from 0.11% to 0.14% in their original test.

This repo's data/loaders.py provides daily OHLCV (open/high/low/close for
the same trading day), so the "buy at today's open, sell at today's close"
mechanic is directly computable without needing next-day price data --
this is a same-day (intraday) hold, distinct from every other strategy in
this repo, which either hold overnight (next-day open/close) or across
multiple days. First same-day open-to-close intraday reversal strategy in
this repo. Distinct from the existing overnight-gap-classification
entries (e.g. 2026-09-20's overnight_gap_dual_classification.py), which
trade the *overnight* gap (yesterday close -> today open) rather than the
*intraday* session (today open -> today close).

Signal logic
------------
- open_pct_change = (open / prior_close) - 1.
- entry (long, held only for that single day): -down_threshold_max <
  open_pct_change < -down_threshold_min (i.e. a "modest" down-open --
  down enough to be a real down-open, but not so far down it signals
  serious follow-through selling). Optionally (require_prior_down_day)
  additionally requires yesterday's close < the day before's close (the
  source's own disclosed improvement).
- Position is held ONLY for that single day: 1 if entry qualifies for
  that specific day, 0 otherwise (no multi-day carry).
- Daily strategy return on a qualifying day = (close/open - 1); 0 on all
  other days. This differs from every other strategy in this repo's
  next-day-shift convention because the entry and exit happen on the SAME
  bar (open->close), matching the source's own explicit same-day design;
  there is therefore no look-ahead risk since both open and close are
  bar-native OHLCV fields for that day, and the entry decision only uses
  information available at the open (yesterday's close, today's open).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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
    down_threshold_min: float = 0.0,
    down_threshold_max: float = 0.005,
    require_prior_down_day: bool = True,
) -> pd.Series:
    """Return a {0,1} same-day long/flat signal series (1 = long that day)."""
    df = _prep(price_df)
    open_ = df["open"]
    close = df["close"]
    prior_close = close.shift(1)

    open_pct_change = (open_ / prior_close) - 1.0
    modest_down_open = (open_pct_change < -down_threshold_min) & (
        open_pct_change > -down_threshold_max
    )

    if require_prior_down_day:
        prior_prior_close = close.shift(2)
        prior_day_down = prior_close < prior_prior_close
        entry = modest_down_open & prior_day_down.fillna(False)
    else:
        entry = modest_down_open

    entry = entry.fillna(False)
    position = entry.astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Same-day (open-to-close) strategy returns, no transaction costs.

    Unlike most strategies in this repo, entry and exit both happen on the
    SAME bar (today's open -> today's close), so no shift(1) is applied --
    the position series here already represents "in a same-day trade" for
    that bar, computed only from information available at the open.
    """
    df = _prep(price_df)
    open_ = df["open"]
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    intraday_ret = (close / open_) - 1.0
    strategy_ret = position * intraday_ret.fillna(0.0)
    return strategy_ret
