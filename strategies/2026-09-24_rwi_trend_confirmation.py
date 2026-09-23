"""Strategy: Random Walk Index (RWI) trend-confirmation threshold crossover
(long only).

Hypothesis (knowledge_base id TBD, this cron trigger):
Per strike.money's Random Walk Index guide
(https://www.strike.money/technical-analysis/random-walk-index):
the Random Walk Index tests whether price movement over a lookback is
statistically distinguishable from noise, by ATR-normalizing the observed
high-low range against what a random walk of that many steps would be
expected to produce. RWI High = (High_t - Low_{t-n}) / (ATR_t * sqrt(n))
measures uptrend significance; RWI Low = (High_{t-n} - Low_t) /
(ATR_t * sqrt(n)) measures downtrend significance (Cynthia Kase's standard
construction, sqrt(n) scaling per random-walk expected-range theory). The
source's own disclosed levels: 0.50 = trend initiation threshold, 1.0 =
strong-trend confirmation threshold; RWI hovering near 0 = ranging/
directionless market to avoid. This iteration operationalizes the
"strong trend" entry: RWI High crossing above `entry_threshold` (1.0)
while RWI High > RWI Low (uptrend dominance) triggers a long entry; exit
when RWI High drops back below `exit_threshold` (0.5, trend initiation
floor) or RWI Low overtakes RWI High (trend reversal). First Random Walk
Index entry in this repo (0 prior KB hits) -- distinct from every existing
ATR-normalized indicator here because RWI's sqrt(n) scaling specifically
tests against the random-walk NULL HYPOTHESIS expected range, not a fixed
volatility band or trend-strength percentile.

Signal logic (long side only)
------------------------------
- ATR: Wilder-style rolling mean of true range over `atr_window`.
- RWI High_t = (High_t - Low_{t-n}) / (ATR_t * sqrt(n)), n=`rwi_period`.
- RWI Low_t = (High_{t-n} - Low_t) / (ATR_t * sqrt(n)).
- Entry: RWI High crosses above `entry_threshold` AND RWI High_t >
  RWI Low_t (uptrend dominance confirmed).
- Exit: RWI High drops below `exit_threshold`, OR RWI Low >= RWI High
  (trend reversal), OR `max_hold_days` time-stop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    return df.sort_index()


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    rwi_period: int = 14,
    atr_window: int = 14,
    entry_threshold: float = 1.0,
    exit_threshold: float = 0.5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    n_bars = len(df)

    atr = _atr(df, atr_window)
    high_n_ago = high.shift(rwi_period)
    low_n_ago = low.shift(rwi_period)

    denom = atr * math.sqrt(rwi_period)
    denom_safe = denom.replace(0, float("nan"))

    rwi_high = (high - low_n_ago) / denom_safe
    rwi_low = (high_n_ago - low) / denom_safe
    rwi_high = rwi_high.fillna(0.0)
    rwi_low = rwi_low.fillna(0.0)

    above_entry = (rwi_high > entry_threshold) & (rwi_high > rwi_low)
    above_entry = above_entry.fillna(False)
    cross_entry = above_entry & (~above_entry.shift(1).fillna(False))

    position = pd.Series(0, index=high.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n_bars):
        if in_position:
            held = i - entry_idx
            exit_cond = (
                rwi_high.iloc[i] < exit_threshold
                or rwi_low.iloc[i] >= rwi_high.iloc[i]
                or held >= max_hold_days
            )
            if exit_cond:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
            continue

        if bool(cross_entry.iloc[i]):
            in_position = True
            entry_idx = i
            position.iloc[i] = 1
            continue

        position.iloc[i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, leverage_cap: float = 1.0, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret * leverage_cap
    return strategy_ret
