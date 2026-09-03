"""Strategy: Gap-down fade -- long only intraday (open-to-close), triggered by
an overnight gap down.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-03-010):
Source: https://daytradingtoolkit.com/strategies/gap-fill-gap-fade-strategy
-- academic literature (Berkman, Koch, Tuttle & Zhang 2012; Aboody, Even-Tov,
Lehavy & Trueman 2018; Akbas, Boehmer, Jiang & Koch 2022, "tug of war"
framing) finds overnight gaps driven by retail sentiment/attention tend to
reverse (fade) during the following intraday session, once daytime
arbitrageurs trade against the overnight order-flow imbalance. The source's
own setup requires intraday/minute data (pre-market volume screens, opening
range triggers) this repo's daily-only loaders don't have -- but the core
academic finding (overnight gap direction predicts an OPPOSITE intraday
open-to-close return) is testable at daily granularity using the existing
`open`/`close` OHLCV columns.

This tests the long-only fade side only (buy the open after a gap DOWN,
sell at the close, betting on a partial intraday reversal upward) since
SAFETY.md/loop convention here is long-only (no shorting the gap-up fade
side). This is structurally distinct from 2026-09-03-007 (overnight_drift,
which HOLDS the close-to-open window and is unconditional/trend-filtered) --
here the position is held over the OPPOSITE sub-daily window (open-to-close,
i.e. the regular trading session) and is conditioned on a gap-down trigger,
not held every night.

Signal logic
------------
- Overnight gap: `gap = open[t] / close[t-1] - 1`.
- Entry: gap < -`gap_threshold` (a meaningfully negative overnight gap).
- Position held ONLY for that day's intraday session (open[t] -> close[t]);
  flat overnight (no close-to-open exposure) and flat on days without a
  qualifying gap-down.
- Long-only, no shorts.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  ({0,1} per-day intraday
        participation flag, not a persistent multi-day position)
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
    gap_threshold: float = 0.01,
) -> pd.Series:
    """Return a {0,1} per-day intraday-session participation flag.

    1 means "buy at today's open, sell at today's close" (fading a gap down);
    0 means flat all day. No look-ahead: the gap is known as of today's open,
    before the day's own intraday move.
    """
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]

    prior_close = close.shift(1)
    gap = (open_ / prior_close - 1.0)

    position = (gap < -gap_threshold).fillna(False).astype(int)
    position.iloc[0] = 0  # no prior close available for bar 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Intraday-only (open[t] -> close[t]) daily returns, gated by the
    gap-down entry flag. Already causal (the gap trigger and the day's own
    intraday return use only same-day open/close and the already-known
    prior close), so no extra 1-day shift is applied here (unlike the
    close-to-close daily-bar strategies elsewhere in this repo).
    """
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    position = generate_signals(price_df, **kwargs)

    intraday_ret = (close / open_ - 1.0).fillna(0.0)
    strategy_ret = position * intraday_ret
    return strategy_ret
