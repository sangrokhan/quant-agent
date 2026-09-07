"""Strategy: 52-week-low base-and-reclaim long entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-081):
Per https://www.tradiecapital.com/blog/52-week-low-stocks -- indiscriminate
dip-buying at a fresh 52-week low is dangerous (momentum literature: recent
losers keep underperforming near-term). The source's own disclosed testable
rule instead requires CONFIRMATION before entry: "buy stocks that made a
52-week low at least N days ago, have since built a base of at least
base_weeks weeks with contracting volume, and today close above the 50-day
moving average for the first time in several months; stop below the base
low." This strategy operationalizes that confirmed-reclaim rule rather than
buying the low itself.

Signal logic
------------
- Track the rolling 252-day low. Record the most recent bar where price hit
  a fresh 252-day low ("the low").
- Require at least `min_days_since_low` trading days have elapsed since that
  low (a base has had time to form) and at most `max_days_since_low` (avoid
  ancient, no-longer-relevant lows).
- Require the low-to-today range ("the base") shows contracting volume:
  average volume over the most recent `base_window` days is below
  `vol_contraction_ratio` x average volume over the `base_window` days
  right after the low was made.
- Require price has been BELOW its 50-day SMA for at least
  `below_sma_min_days` of the last `below_sma_lookback` days (i.e. genuinely
  out of favor, not already recovered).
- Entry (long): close crosses above SMA(reclaim_sma_window) for the first
  time after satisfying all the above (the "reclaim").
- Exit: close crosses back below SMA(reclaim_sma_window) (stop/failed
  reclaim) or a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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
    low_window: int = 252,
    min_days_since_low: int = 40,
    max_days_since_low: int = 180,
    base_window: int = 20,
    vol_contraction_ratio: float = 0.85,
    below_sma_lookback: int = 120,
    below_sma_min_days: int = 60,
    reclaim_sma_window: int = 50,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=close.index)

    rolling_low = close.rolling(low_window, min_periods=low_window // 2).min()
    is_fresh_low = close <= rolling_low + 1e-9

    sma_reclaim = close.rolling(reclaim_sma_window).mean()
    below_sma = close < sma_reclaim
    below_sma_count = below_sma.rolling(below_sma_lookback, min_periods=1).sum()

    avg_vol_short = volume.rolling(base_window, min_periods=1).mean()

    n = len(close)
    position = pd.Series(0, index=close.index, dtype=int)

    last_low_idx = None
    last_low_post_vol = None
    in_position = False
    entry_idx = 0
    was_below_reclaim = False

    close_vals = close.values
    sma_vals = sma_reclaim.values
    below_count_vals = below_sma_count.values
    is_low_vals = is_fresh_low.values
    avgvol_vals = avg_vol_short.values

    for i in range(n):
        if bool(is_low_vals[i]):
            last_low_idx = i
            # volume shortly after the low (base start)
            end = min(i + base_window, n)
            last_low_post_vol = volume.iloc[i:end].mean() if end > i else None

        if in_position:
            held = i - entry_idx
            close_below_sma = (
                not pd.isna(sma_vals[i]) and close_vals[i] < sma_vals[i]
            )
            if close_below_sma or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
            continue

        # Not in position: check entry conditions
        eligible = False
        if (
            last_low_idx is not None
            and not pd.isna(sma_vals[i])
            and last_low_post_vol is not None
            and last_low_post_vol > 0
        ):
            days_since_low = i - last_low_idx
            if min_days_since_low <= days_since_low <= max_days_since_low:
                base_vol_contracting = avgvol_vals[i] <= vol_contraction_ratio * last_low_post_vol
                below_days = below_count_vals[i]
                if base_vol_contracting and below_days >= below_sma_min_days:
                    # reclaim = crossing above sma this bar (was below on prior bar)
                    prior_below = i > 0 and not pd.isna(sma_vals[i - 1]) and close_vals[i - 1] < sma_vals[i - 1]
                    curr_above = close_vals[i] >= sma_vals[i]
                    if prior_below and curr_above:
                        eligible = True

        if eligible:
            in_position = True
            entry_idx = i
            position.iloc[i] = 1
        else:
            position.iloc[i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
