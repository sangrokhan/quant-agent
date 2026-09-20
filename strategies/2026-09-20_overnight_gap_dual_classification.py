"""Strategy: Overnight Gap Dual Classification (Fill vs Go), daily-bar adaptation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-XXX):
Per https://pinescriptforge.com/strategy/overnight-gap ("Overnight Gap
Strategy"), the source classifies each session's open-vs-prior-close gap
into one of two regimes and trades each differently, rather than treating
all gaps uniformly (unlike the prior unconditional gap-fade strategy in this
repo, id 2026-09-16-079, which was rejected):

- "Fill" candidate: small gap (|gap%| < fill_gap_thresh) with LOW volume
  conviction at the open (volume_ratio < vol_low_ratio, i.e. today's volume
  well below its trailing average) -> fade the gap (bet it closes back
  toward the prior close). Source: "Gap fill: fade gaps < 0.5% with low
  volume (enter against gap direction)". Exit target: prior close.
- "Go" candidate: large gap (|gap%| > go_gap_thresh) with HIGH volume
  conviction (volume_ratio > vol_high_ratio) -> trade WITH the gap direction
  (continuation). Source: "Gap & go: trade with gaps > 1% that have strong
  volume at open". Exit: trail (approximated here as full open-to-close
  exposure, since daily bars have no intraday VWAP).
- Both regimes: "stop at 50% of gap distance against position" -- approximated
  on daily bars by capping that day's realized loss at
  stop_frac * gap_distance (using the day's own high/low would require
  intraday data; here we cap the open-to-close return directly, which is a
  conservative simplification of the same rule).

This is a daily-bar approximation of an intraday setup (real edge is
open-to-close, single-day exposure, flat overnight) -- distinct from
2026-09-16-079's unconditional single-threshold gap fade because it: (1)
requires a volume-conviction filter, (2) has two DIFFERENT thresholds/
directions for small-quiet vs large-loud gaps, and (3) applies an explicit
stop-loss cap on the realized return.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
        Daily strategy returns (position-weighted intraday open-to-close
        exposure; flat overnight by construction).
    generate_signals(price_df, **params) -> pd.Series
        {-1, 0, 1} position series (short/flat/long) for the day's
        open-to-close leg.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    """Load and, if the data looks intraday (crypto loader default is
    hourly), resample to daily OHLCV bars -- this strategy's gap logic is
    inherently a daily-bar (session open vs prior session close) concept."""
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    if len(df.index) > 1:
        median_gap = pd.Series(df.index).diff().median()
        if pd.notna(median_gap) and median_gap < pd.Timedelta(hours=20):
            df = df.resample("1D").agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                }
            ).dropna()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    fill_gap_thresh: float = 0.005,
    go_gap_thresh: float = 0.01,
    vol_window: int = 20,
    vol_low_ratio: float = 0.8,
    vol_high_ratio: float = 1.2,
) -> pd.Series:
    """Return a {-1, 0, 1} short/flat/long position series for each day's
    open-to-close leg."""
    df = _prep(price_df)
    open_ = df["open"]
    close = df["close"]
    volume = df["volume"]

    prior_close = close.shift(1)
    gap_pct = (open_ - prior_close) / prior_close

    vol_avg = volume.shift(1).rolling(vol_window).mean()
    volume_ratio = volume / vol_avg

    gap_dir = np.sign(gap_pct)

    is_fill = (gap_pct.abs() < fill_gap_thresh) & (volume_ratio < vol_low_ratio)
    is_go = (gap_pct.abs() > go_gap_thresh) & (volume_ratio > vol_high_ratio)

    position = pd.Series(0, index=close.index, dtype=int)
    position[is_fill] = -gap_dir[is_fill].astype(int)
    position[is_go] = gap_dir[is_go].astype(int)
    # If both conditions somehow overlap (shouldn't with these threshold
    # relationships since fill requires small gap and go requires large gap),
    # "go" (the source's stronger-conviction regime) takes precedence.
    position[is_go] = gap_dir[is_go].astype(int)
    position = position.fillna(0).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    fill_gap_thresh: float = 0.005,
    go_gap_thresh: float = 0.01,
    vol_window: int = 20,
    vol_low_ratio: float = 0.8,
    vol_high_ratio: float = 1.2,
    stop_frac: float = 0.5,
) -> pd.Series:
    """Position-weighted open-to-close daily returns, with a stop-loss cap
    at stop_frac * gap_distance. The stop is checked against the day's own
    intraday high/low (not just the close) -- if breached, the trade is
    assumed to exit at the stop level; otherwise the full open-to-close move
    is realized. No transaction costs applied here."""
    df = _prep(price_df)
    open_ = df["open"]
    high = df["high"]
    low = df["low"]
    close = df["close"]

    position = generate_signals(
        price_df,
        fill_gap_thresh=fill_gap_thresh,
        go_gap_thresh=go_gap_thresh,
        vol_window=vol_window,
        vol_low_ratio=vol_low_ratio,
        vol_high_ratio=vol_high_ratio,
    )

    prior_close = close.shift(1)
    gap_distance_pct = (open_ - prior_close).abs() / prior_close
    stop_dist = stop_frac * gap_distance_pct.fillna(0.0)

    raw_oc_return = (close - open_) / open_
    # Worst adverse excursion actually observed intraday, per direction:
    # long -> adverse move is measured via the low; short -> via the high.
    long_adverse = (low - open_) / open_  # <= 0 typically
    short_adverse = (open_ - high) / open_  # <= 0 typically (loss if high > open)

    long_stopped = long_adverse <= -stop_dist
    short_stopped = short_adverse <= -stop_dist

    long_ret = raw_oc_return.where(~long_stopped, -stop_dist)
    short_ret = (-raw_oc_return).where(~short_stopped, -stop_dist)

    strategy_ret = pd.Series(0.0, index=close.index)
    strategy_ret[position == 1] = long_ret[position == 1]
    strategy_ret[position == -1] = short_ret[position == -1]
    strategy_ret = strategy_ret.fillna(0.0)
    return strategy_ret
