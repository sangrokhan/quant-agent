"""Strategy: Bitcoin halving-cycle "500-day rule" (long/short calendar rotation).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-096):
The "500-day rule" (popularized by TradingView user Money_addixt, echoed by
Crypto Rover/Binance Square/CoinDesk): go long BTC 500 days before each
halving event, hold through the halving and the subsequent bull run, then
close the long and go short exactly 500 days after the halving to target
the historical post-halving cycle correction/bear phase. Flat between
cycles (outside the [H-500d, H+500d] window). Purely calendar-driven, no
technical indicators. This repo tests it long-only (no shorting per
SAFETY.md/repo convention -- the short leg is replaced with "flat" rather
than an actual short position).

Signal logic
------------
- Known halving dates (UTC): 2012-11-28, 2016-07-09, 2020-05-11, 2024-04-20.
  (Next projected ~2028-04, outside this repo's ~2019-2026 backtest window.)
- For each halving date H: position = 1 (long) for calendar days in
  [H - pre_days, H + post_days_flip], i.e. the "buy 500 days before, hold
  through halving" phase.
- Position = 0 (flat) for calendar days in (H + post_days_flip, H + post_days_flip
  + post_flat_days], approximating the "close long" half of the rule
  without going short (long-only constraint).
- Position = 0 (flat) at all other times (before the pre-window of the next
  halving, after the post-window of the prior one).
- Since our backtest window only fully contains the 2020-05-11 and
  2024-04-20 halvings (2019-2026 sample), those are the two cycles actually
  exercised.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd

HALVING_DATES = [
    pd.Timestamp("2012-11-28", tz="UTC"),
    pd.Timestamp("2016-07-09", tz="UTC"),
    pd.Timestamp("2020-05-11", tz="UTC"),
    pd.Timestamp("2024-04-20", tz="UTC"),
]


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    pre_days: int = 500,
    post_days_flip: int = 500,
) -> pd.Series:
    """Return a {0,1} long/flat position series (long-only 500-day-rule)."""
    df = _prep(price_df)
    idx = df.index
    if idx.tz is None:
        idx_utc = idx.tz_localize("UTC")
    else:
        idx_utc = idx.tz_convert("UTC")

    position = pd.Series(0, index=df.index, dtype=int)
    for h in HALVING_DATES:
        window_start = h - pd.Timedelta(days=pre_days)
        window_end = h + pd.Timedelta(days=post_days_flip)
        mask = (idx_utc >= window_start) & (idx_utc <= window_end)
        position.loc[mask] = 1
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
