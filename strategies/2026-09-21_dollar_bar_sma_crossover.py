"""Strategy: Dollar-bar SMA crossover trend-following (information-driven
bar sampling applied to daily OHLCV+volume data).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-207):
Source: https://twowaymind.com/article-information-driven-bars ("Information
-Driven Bars: Tick, Volume & Dollar Sampling for Market Microstructure",
Aug 2026, summarizing Lopez de Prado's "Advances in Financial Machine
Learning"). The article argues that sampling bars by fixed wall-clock time
distorts statistical properties of returns (non-IID, heteroskedastic, fat
tails) because information/activity does not arrive at a constant rate, and
that sampling by cumulative dollar value traded ("dollar bars") instead
produces better-behaved, closer-to-IID return series that downstream trend
models should benefit from. True tick-level dollar bars require trade-level
data this repo's data/loaders.py does not provide (OHLCV only) -- this
iteration approximates the CONCEPT using daily OHLCV+volume: treat each
day's dollar volume (close * volume) as the activity measure, accumulate
consecutive trading days into a variable-length "dollar bar" whenever
cumulative dollar volume crosses a rolling, causally-computed threshold
(a multiple of the trailing average daily dollar volume), then run a simple
SMA-crossover trend-following signal on the resampled BAR-close series
(rather than on the raw daily-close series) and map bar-level positions back
onto the daily calendar. This is a bar-sampling-method novelty (distinct
from any indicator-family variant already in this KB) rather than a new
indicator.

Signal logic
------------
- daily_dollar_vol = close * volume.
- threshold_t = rolling_mean(daily_dollar_vol, vol_window).shift(1) *
  target_days_per_bar (causal: uses only data available before day t).
- Accumulate daily_dollar_vol day-by-day; when the running total within the
  current bar reaches threshold_t, close the bar and start a new one.
  (During the vol_window warmup, threshold is NaN and all days fall in bar 0.)
- bar_close = last daily close within each completed/in-progress bar.
- fast_sma / slow_sma computed on the bar_close series (bar-index, not
  day-index) over `fast_bars`/`slow_bars` bars.
- bar_position = 1 if fast_sma > slow_sma else 0, SHIFTED by one bar (so a
  bar's position is decided using only prior, already-closed bars' SMAs --
  no look-ahead within the still-forming bar).
- Map bar_position back onto each day belonging to that bar to get the daily
  {0,1} position series.

Interface contract (validation/grid_test.py, validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def generate_signals(
    price_df: pd.DataFrame,
    vol_window: int = 60,
    target_days_per_bar: float = 5.0,
    fast_bars: int = 10,
    slow_bars: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series (daily granularity)."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=close.index)

    daily_dollar_vol = (close * volume).fillna(0.0)
    avg_dollar_vol = daily_dollar_vol.rolling(vol_window).mean().shift(1)
    threshold = avg_dollar_vol * target_days_per_bar

    n = len(close)
    bar_id = np.zeros(n, dtype=int)
    cum = 0.0
    current_bar = 0
    thr_vals = threshold.to_numpy()
    dv_vals = daily_dollar_vol.to_numpy()
    for i in range(n):
        thr = thr_vals[i]
        bar_id[i] = current_bar
        if np.isnan(thr) or thr <= 0:
            continue
        cum += dv_vals[i]
        if cum >= thr:
            current_bar += 1
            cum = 0.0

    bar_series = pd.Series(bar_id, index=close.index)
    bar_close = close.groupby(bar_series).last()

    fast_sma = bar_close.rolling(fast_bars).mean()
    slow_sma = bar_close.rolling(slow_bars).mean()
    bar_position = (fast_sma > slow_sma).astype(int)
    # Shift by 1 bar: a bar's position is decided from the PRIOR bar's
    # already-closed SMA values, never the bar's own (still-forming) data.
    bar_position = bar_position.shift(1).fillna(0).astype(int)

    position = bar_series.map(bar_position).fillna(0).astype(int)
    position.index = close.index
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    # Additional 1-day shift (standard convention in this repo): yesterday's
    # signal determines today's return exposure.
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
