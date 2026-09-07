"""Strategy: SPY-style Opening Gap-Down Fill (partial-target mean reversion).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-016):
Per QuantifiedStrategies.com's own disclosed, non-paywalled numeric rule
(https://www.quantifiedstrategies.com/gap-fill-trading-strategies/, author's
own SPY backtest 2010-2012, 110 fills/98 winners/avg 0.19% per fill): a
moderate overnight gap DOWN (open between -0.6% and -0.15% below the prior
close -- deliberately excluding both tiny "noise" gaps and large gaps, which
the source's own data showed mean-revert less reliably) is a same-day
mean-reversion long entry at the open, additionally gated by a prior-day
Internal Bar Strength (IBS = (close-low)/(high-low)) below 0.25 (source's
own stated filter for SPY's "mean-reversion tendencies" -- fewer but higher-
quality fills). The trade targets 0.75 of the gap size (not a full fill,
per source's own finding this improves the win rate/average), exiting at
that intraday target if touched, otherwise exiting flat at the same day's
close (no overnight hold, no stop beyond the close exit).

This is distinct from the already-rejected 2026-09-03-010 (a simple
academic-literature gap-down fade with no gap-size band, no partial-target
exit rule, and no IBS entry filter) -- the QuantifiedStrategies rule adds
three concrete, source-specific mechanics (gap-size band, IBS filter,
partial-fill target) that make this a genuinely different, more specific
hypothesis, not a re-test of the same idea.

Signal logic (single-day, intraday open-to-close trade, no overnight hold)
----------------------------------------------------------------------
- gap_pct[t] = open[t] / close[t-1] - 1
- ibs[t-1] = (close[t-1] - low[t-1]) / (high[t-1] - low[t-1])
- Entry (long, at day t's open) when:
    gap_down_max <= gap_pct[t] <= gap_down_min   (e.g. -0.6% <= gap <= -0.15%,
    both negative, gap_down_max is the more-negative bound)
    AND ibs[t-1] < ibs_threshold (0.25)
- Target price = open[t] + target_fraction * abs(gap_pct[t]) * close[t-1]
  (target_fraction of the gap size back toward the prior close).
- Exit: if day t's high[t] >= target price, exit at the target (capped
  gain); otherwise exit flat at day t's close (no stop beyond that).
- Flat every other day -- this is a pure single-day trade strategy, not a
  multi-day hold; the position never carries overnight.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series (daily strategy
        returns; nonzero only on entry days, using intraday open/high/close
        approximation described above -- 0.0 on every other day)
    generate_signals(price_df, **params) -> pd.Series (1 on entry days, 0
        otherwise -- exposed for paper_trading/simulator.py compatibility;
        note this does NOT mean "holding a position the following day" the
        way other strategies in this repo do, since trades are same-day
        open-to-close only)
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
    gap_down_min: float = -0.0015,
    gap_down_max: float = -0.006,
    ibs_threshold: float = 0.25,
    target_fraction: float = 0.75,
) -> pd.Series:
    """Return a {0,1} series: 1 on days the gap-fill entry condition fires."""
    df = _prep(price_df)
    open_ = df["open"]
    high = df["high"]
    low = df["low"]
    close = df["close"]

    prior_close = close.shift(1)
    prior_high = high.shift(1)
    prior_low = low.shift(1)
    prior_range = (prior_high - prior_low).replace(0, pd.NA)
    prior_ibs = (prior_close - prior_low) / prior_range

    gap_pct = open_ / prior_close - 1.0

    # gap_down_min/-max are both negative; gap_down_max is more negative
    # (the wider/lower bound), gap_down_min is closer to zero (the tighter
    # bound) -- entry requires gap_down_max <= gap_pct <= gap_down_min.
    lo_bound = min(gap_down_min, gap_down_max)
    hi_bound = max(gap_down_min, gap_down_max)

    entry = (gap_pct >= lo_bound) & (gap_pct <= hi_bound) & (prior_ibs < ibs_threshold)
    entry = entry.fillna(False)

    return entry.astype(int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Same-day open-to-close (or open-to-target) returns on entry days,
    0.0 every other day. No overnight hold -- position never carries past
    the same day's close.
    """
    df = _prep(price_df)
    open_ = df["open"]
    high = df["high"]
    close = df["close"]

    target_fraction = kwargs.get("target_fraction", 0.75)
    entry = generate_signals(price_df, **kwargs)

    prior_close = close.shift(1)
    gap_pct = open_ / prior_close - 1.0
    gap_size = (open_ - prior_close).abs()  # in price units
    target_price = open_ + target_fraction * gap_size

    hit_target = high >= target_price
    ret_if_target = (target_price / open_) - 1.0
    ret_if_close = (close / open_) - 1.0

    trade_ret = ret_if_target.where(hit_target, ret_if_close)
    strategy_ret = trade_ret.where(entry == 1, 0.0)
    strategy_ret = strategy_ret.fillna(0.0)
    return strategy_ret
