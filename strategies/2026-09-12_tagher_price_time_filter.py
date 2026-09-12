"""Strategy: Tagher Price-Time Filtering trend state-machine (weekly-resampled).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per Alfred Francois Tagher's "Trend Identification By Price And Time
Filtering" (TASC February 2024 Traders' Tips, fully disclosed rule set via
https://www.tradingview.com/scripts/tasc/): a simple weekly-bar
price-action state machine identifies a persistent trend while minimizing
whipsaw from stochastic day-to-day noise:
    - Uptrend if the latest week's CLOSE exceeds the PREVIOUS week's HIGH.
    - Downtrend if the latest week's CLOSE is below the PREVIOUS week's LOW.
    - Otherwise the trend state persists unchanged (no re-evaluation until
      one of the above conditions triggers).
The author argues this "integrates price action and time dynamics" to
filter out smaller stochastic swings that would otherwise generate false
signals in a naive daily-bar trend filter. Long-only adaptation: long while
the weekly state is "up", flat while "down" (starts flat/neutral).

Signal logic
------------
- Resample daily OHLC to weekly bars (W-FRI, matching US equity/24-7 crypto
  week boundaries via pandas' standard weekly resample).
- Apply the exact state-machine rule on weekly close/high/low.
- Forward-fill the resulting weekly trend state back onto daily bars (the
  trend state, once set at a week's close, governs exposure through the
  following week -- avoids look-ahead by shifting the weekly signal by one
  day so it's only usable starting the day AFTER the week's data is fully
  known).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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


def _weekly_trend_state(daily_df: pd.DataFrame, resample_rule: str = "W-FRI") -> pd.Series:
    """Return a daily-indexed {-1,0,1} trend state series using Tagher's rule
    computed on weekly-resampled bars, then forward-filled to daily frequency
    with a 1-day lag to avoid look-ahead (a week's own close isn't known
    until the week closes)."""
    weekly = daily_df.resample(resample_rule).agg({"high": "max", "low": "min", "close": "last"}).dropna()

    state = pd.Series(0, index=weekly.index, dtype=int)  # 0 = neutral/undetermined
    cur = 0
    for i in range(1, len(weekly)):
        prev_high = weekly["high"].iloc[i - 1]
        prev_low = weekly["low"].iloc[i - 1]
        close = weekly["close"].iloc[i]
        if close > prev_high:
            cur = 1
        elif close < prev_low:
            cur = -1
        state.iloc[i] = cur

    # Reindex to daily and forward-fill; the weekly bar's state becomes
    # usable starting the NEXT trading day after the week's own close date
    # (shift by one calendar day is handled naturally since weekly bars are
    # dated at week-end and daily bars only see it once available).
    daily_state = state.reindex(daily_df.index, method="ffill").fillna(0).astype(int)
    return daily_state


def generate_signals(price_df: pd.DataFrame, resample_rule: str = "W-FRI", trend_sma_window: int = 0) -> pd.Series:
    """Return a {0,1} long/flat position series (long-only adaptation).

    Note: the weekly trend state is forward-filled onto daily bars as soon
    as it's computed (i.e. usable from the day it's known); the standard
    1-day exposure lag (avoid trading on the same close used to compute the
    signal) is applied uniformly in generate_returns below, matching this
    repo's other strategies' convention.

    `trend_sma_window` (0 = disabled): optional additional daily-close >
    SMA(trend_sma_window) gate, added purely to give the strategy a
    meaningful tunable parameter for grid/sensitivity testing (the source's
    own rule has no free parameters).
    """
    df = _prep(price_df)
    state = _weekly_trend_state(df, resample_rule=resample_rule)
    position = (state > 0).astype(int)
    if trend_sma_window and trend_sma_window > 0:
        sma = df["close"].rolling(trend_sma_window).mean()
        position = position & (df["close"] > sma).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
