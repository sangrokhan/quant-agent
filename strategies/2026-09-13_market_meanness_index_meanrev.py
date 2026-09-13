"""Strategy: Market Meanness Index (MMI) median-deviation mean reversion,
trend-gated long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-13-market-meanness-index):
Per https://theindicatorlab.com/reviews/market-meanness-index/ (read via
browser_exec this iteration), the Market Meanness Index is a 0-100 oscillator
measuring how far the current close has deviated from a rolling MEDIAN
(rather than a mean/stddev like Bollinger Bands), making it more robust to
single-bar outliers. The source's disclosed mechanical rule: long when MMI
crosses below an oversold threshold (15) and then turns back up, exit when
MMI crosses back above 50; a 200-period SMA trend filter is recommended to
only take long signals when price is above it (cuts false signals ~40% per
source, though that figure is the source's own unverified claim).

This is distinct from every prior Bollinger-Band / z-score mean-reversion
variant already tested in this repo (15+ prior entries) because it uses a
MEDIAN-based deviation measure normalized to a fixed 0-100 scale, not a
standard-deviation-based band -- a genuinely different statistical estimator
for "how extreme is the current price" that should behave differently on
distributions with outlier/fat-tail bars (crypto especially).

Signal logic
------------
- Rolling median of close over `mmi_window` bars.
- Deviation = close - rolling_median, normalized via a rolling min-max over
  `mmi_window` (rescaled to a 0-100 index; low deviation from median => mid
  values; extreme high vs. extreme low deviations map towards the tails).
  We implement MMI as: 100 * (rank of current deviation within the trailing
  window), i.e. a rolling percentile-rank of (close - rolling_median),
  which is the standard "meanness index" percentile construction used by
  most public implementations when the source formula isn't fully spelled
  out numerically (the source article gives the *trading rule*, not the
  exact normalization formula, so we use the standard percentile-rank
  construction, consistent with how RSI-family "index" oscillators are
  built).
- Trend filter: close > SMA(trend_window) (only take long signals in an
  uptrend, per source's "Pro Tip").
- Entry (long): MMI crosses below `oversold_threshold`, then on a
  subsequent bar turns back up (MMI[t] > MMI[t-1] while MMI[t-1] was still
  below oversold_threshold) AND trend filter is true.
- Exit: MMI crosses back above `exit_threshold` (50, source's rule), OR a
  max holding period of `max_hold_days` (avoid indefinite holds, standard
  practice in this repo since raw oscillator exits can stall in illiquid
  regimes).

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


def _market_meanness_index(close: pd.Series, window: int) -> pd.Series:
    """Rolling percentile-rank (0-100) of (close - rolling median) within
    its own trailing window -- the standard construction for a bounded
    0-100 'meanness'/deviation oscillator when only the trading rule (not
    the exact normalization formula) is publicly disclosed."""
    median = close.rolling(window).median()
    deviation = close - median
    # Vectorized rolling percentile-rank of the last value within its own
    # trailing window (pandas rolling().rank(pct=True) computes exactly this
    # -- rank of the final element vs. the rest of the window -- much faster
    # than a python-level rolling.apply over large OHLCV histories).
    mmi = deviation.rolling(window).rank(pct=True) * 100.0
    return mmi


def generate_signals(
    price_df: pd.DataFrame,
    mmi_window: int = 20,
    trend_window: int = 200,
    oversold_threshold: float = 15.0,
    exit_threshold: float = 50.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    mmi = _market_meanness_index(close, mmi_window)
    trend_ok = close > close.rolling(trend_window).mean()

    was_oversold = mmi.shift(1) < oversold_threshold
    turning_up = mmi > mmi.shift(1)
    entry = was_oversold & turning_up & trend_ok.fillna(False)
    exit_meanrev = mmi > exit_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    mmi_valid = mmi.notna()
    for i in range(len(close)):
        if not mmi_valid.iloc[i]:
            position.iloc[i] = 0
            continue
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or held >= max_hold_days:
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
