"""Strategy: Corwin-Schultz bid-ask spread regime-exit, gated by SMA trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-002),
sourced from https://www.tradingview.com/script/ji4eKKuZ-Corwin-Schultz-Spread-Bands/
(visited this iteration, "Corwin-Schultz Spread Bands [forexobroker]"),
which itself implements the peer-reviewed Corwin & Schultz (2012, Journal of
Finance) two-bar high-low bid-ask spread estimator: daily high/low ranges
widen mechanically both from volatility AND from the bid-ask bounce, and the
CS estimator statistically separates the two, producing a rolling estimate
of the effective bid-ask spread using ONLY OHLC data (no order-flow/quote
data required, unlike Kyle's lambda or Roll's serial-covariance estimator,
both investigated this iteration but rejected at the novelty/feasibility
stage since they require intraday signed order flow this repo's
data/loaders.py cannot provide).

Economic rationale: an elevated estimated spread signals "liquidity stress"
(wider effective transaction costs, often coinciding with uncertainty/thin
markets); when the stress regime resolves (estimated spread reverts back
below its own rolling threshold), and the prevailing trend is bullish, it
is a historically favorable entry window -- liquidity stress has passed but
the trend is intact. This is the source's own disclosed mechanical rule,
not just a general spread commentary.

First Corwin-Schultz-spread-estimator strategy in this repo (0 prior hits
for "Corwin-Schultz", "spread estimator", "bid-ask spread", or "Roll
spread" in strategies_index.jsonl as of this iteration).

Signal logic
------------
- For each pair of adjacent daily bars t-1, t:
      beta  = ln(H_t/L_t)^2 + ln(H_{t-1}/L_{t-1})^2
      gamma = ln(max(H_t,H_{t-1}) / min(L_t,L_{t-1}))^2
      alpha = (sqrt(2*beta) - sqrt(beta)) / (3 - 2*sqrt(2))
              - sqrt(gamma / (3 - 2*sqrt(2)))
      raw_spread = 2*(exp(alpha)-1) / (1+exp(alpha)), clamped to [0, 1]
  (Corwin & Schultz 2012's own two-bar estimator, per the source.)
- Smooth raw_spread with an EMA (`spread_smooth`) for a stable series.
- Rolling regime stats over `regime_lookback` bars: median + `stdev_mult` *
  stdev of the smoothed spread = stress threshold.
- "In stress" = smoothed spread > threshold. "Exiting stress" = was in
  stress on the prior bar, not in stress now (a stress-regime resolution
  event).
- Long entry: stress-exit event AND close > SMA(trend_window) (bullish
  trend filter, source's own default 20-period SMA, generalized here as a
  tunable parameter).
- Exit to flat: close crosses below the trend SMA (risk-off exit), OR
  after `max_hold_days` bars (time-stop backstop, consistent with this
  repo's other regime-triggered strategies).
- Long-only, consistent with this repo's other strategies and SAFETY.md.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns, position lagged by 1 day to avoid look-ahead bias)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

_K = 3 - 2 * np.sqrt(2)


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _corwin_schultz_spread(high: pd.Series, low: pd.Series, smooth: int) -> pd.Series:
    log_hl = np.log(high / low)
    beta = log_hl ** 2 + log_hl.shift(1) ** 2

    hh = pd.concat([high, high.shift(1)], axis=1).max(axis=1)
    ll = pd.concat([low, low.shift(1)], axis=1).min(axis=1)
    gamma = (np.log(hh / ll)) ** 2

    with np.errstate(invalid="ignore"):
        alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / _K - np.sqrt(gamma / _K)

    raw_spread = 2 * (np.exp(alpha) - 1) / (1 + np.exp(alpha))
    raw_spread = raw_spread.clip(lower=0.0, upper=1.0)
    smoothed = raw_spread.ewm(span=smooth, adjust=False, min_periods=smooth).mean()
    return smoothed


def generate_signals(
    price_df: pd.DataFrame,
    spread_smooth: int = 5,
    regime_lookback: int = 100,
    stdev_mult: float = 1.0,
    trend_window: int = 20,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    spread = _corwin_schultz_spread(high, low, spread_smooth)

    rolling_median = spread.rolling(regime_lookback, min_periods=regime_lookback).median()
    rolling_std = spread.rolling(regime_lookback, min_periods=regime_lookback).std()
    threshold = rolling_median + stdev_mult * rolling_std

    in_stress = (spread > threshold).fillna(False)
    exiting_stress = in_stress.shift(1).fillna(False) & (~in_stress)

    sma_trend = close.rolling(trend_window, min_periods=trend_window).mean()
    above_trend = (close > sma_trend).fillna(False)

    entry_event = exiting_stress & above_trend

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_count = 0
    entry_arr = entry_event.values
    above_trend_arr = above_trend.values

    for i in range(len(df.index)):
        if in_position:
            hold_count += 1
            if (not above_trend_arr[i]) or hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_arr[i]:
                in_position = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **params)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
