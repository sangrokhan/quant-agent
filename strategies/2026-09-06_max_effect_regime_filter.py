"""Strategy: Single-symbol "MAX effect" time-series adaptation -- fade the
best single day of the prior month.

Hypothesis (see knowledge_base id 2026-09-06-162):
Per the academic "MAX effect" literature (Bali, Cakici & Whitelaw 2011, and
follow-on work surfaced via search, e.g. the Emerald Publishing / MDPI / SSRN
results for "MAX maximum daily return past month lottery stocks reversal"):
stocks with the highest maximum single-DAY return over the prior
`lookback_days` (~1 month = 21 trading days) subsequently underperform --
"lottery stocks" get bid up by return-chasing/gambling-preference investors
and then mean-revert as that overpricing unwinds. The original research is
a CROSS-SECTIONAL decile-sort across a stock universe, which this repo's
single-symbol `grid_test.py` framework cannot replicate directly (no
cross-sectional ranking infrastructure) -- adapted here as a TIME-SERIES
analog on a single symbol: whenever a symbol's own trailing-month maximum
single-day return is unusually large RELATIVE TO ITS OWN HISTORY (top
`max_percentile` percentile of its own trailing `history_window`-day
rolling-max-return distribution), treat that as a timing signal that the
recent extreme up-day was a lottery-like/overreaction event likely to
partially mean-revert -- short-term fade (long the day AFTER the percentile
condition ends, betting on stabilization... actually tested here as a
SHORT-side fade, i.e. going flat/avoiding long exposure) is tested as: stay
OUT of a would-be trend-following long whenever the recent-extreme-day
condition holds, only re-entering once it normalizes. This is a defensive/
regime-filter framing (not a naked short, keeping with this repo's
long-only convention) that lets us test the reversal-after-lottery-day
intuition without requiring a cross-sectional universe.

Concretely (long-only, single-symbol):
- Compute daily returns and their trailing `history_window`-day rolling max
  (the "MAX" statistic, recomputed daily over the trailing month-equivalent
  window instead of calendar-month for daily-bar granularity).
- Trend filter: close > SMA(`trend_window`) (only take longs in an uptrend,
  consistent with this repo's convention, since MAX-effect reversal is a
  downside-risk signal, not a standalone directional edge).
- Entry (long): in an uptrend AND today's rolling-max return has DECAYED
  back below its own `max_percentile`-percentile threshold (computed over a
  trailing `percentile_window`-day history) -- i.e. we deliberately avoid
  entering RIGHT AFTER a lottery-day spike (when the crowd is still
  chasing) and instead enter once that recent-extreme-day effect has aged
  out of the rolling window, consistent with the source's finding that the
  overpricing/reversal plays out over the following weeks.
- Exit: close crosses back below SMA(trend_window) (trend filter breaks),
  OR the rolling-max return re-enters the extreme percentile (a fresh
  lottery day appearing -- get defensive again), OR a `max_hold_days`
  time-stop.

First MAX-effect-inspired reversal/regime-filter strategy in this repo --
distinct from all momentum/trend-following strategies already tested since
this one explicitly AVOIDS entering right after extreme up-moves rather
than chasing them.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
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
    history_window: int = 21,
    percentile_window: int = 252,
    max_percentile: float = 0.90,
    trend_window: int = 100,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    daily_ret = close.pct_change()
    rolling_max_ret = daily_ret.rolling(history_window).max()
    extreme_threshold = rolling_max_ret.rolling(percentile_window, min_periods=history_window).quantile(max_percentile)

    is_extreme = rolling_max_ret >= extreme_threshold

    sma = close.rolling(trend_window).mean()
    uptrend = close > sma

    entry = uptrend.fillna(False) & (~is_extreme.fillna(True))
    exit_trend_break = ~uptrend.fillna(False)
    exit_extreme_reappears = is_extreme.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trend_break.iloc[i]) or bool(exit_extreme_reappears.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
