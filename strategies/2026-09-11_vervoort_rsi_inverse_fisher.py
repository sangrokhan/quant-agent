"""Strategy: Vervoort Smoothed RSI Inverse Fisher Transform, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-007),
sourced from https://traders.com/documentation/feedbk_docs/2010/10/traderstips.html
(TASC October 2010 Traders' Tips, visited this iteration): Sylvain
Vervoort's "Smoothed RSI Inverse Fisher Transform" indicator, per the
disclosed EasyLanguage source:

1. Smooth close with a 10-stage nested "rainbow" weighted moving average
   (each stage a WMA(2) of the prior stage, final value a weighted blend
   of all 10 stages: weights 5,4,3,2,1,1,1,1,1,1 over 20).
2. Compute a standard RSI(RSI_period=4) of that smoothed rainbow price.
3. X = 0.1 * (RSI - 50)  (rescale to roughly [-5, 5]).
4. EMA1 = EMA(X, EMA_period=4); EMA2 = EMA(EMA1, EMA_period=4);
   Difference = EMA1 - EMA2; Z1EMA = EMA1 + Difference (Vervoort's
   zero-lag EMA correction).
5. InverseFisher = ((exp(2*Z1EMA)-1)/(exp(2*Z1EMA)+1) + 1) * 50
   (squashes to roughly [0, 100], saturating hard toward the extremes).

Source's own disclosed rule: buy when InverseFisher crosses above 12
(LongTrigger), sell short when it crosses below 88 (ShortTrigger). This
repo adapts the short leg into a long-only exit: flat when InverseFisher
crosses back below an `exit_level` (default 50, the oscillator's own
centerline) rather than reversing to short, consistent with this repo's
long-only scope (SAFETY.md).

Distinct from all prior Fisher-Transform-family strategies in this repo
(2026-09-04-051, 2026-09-05-086, 2026-09-08-029, 2026-09-11-001) since
those apply the (forward) Fisher Transform directly to price or another
oscillator's raw values; this is the INVERSE Fisher Transform applied to
a double-EMA-smoothed, zero-lag-corrected RSI of a 10-stage rainbow-MA-
smoothed price -- a substantially different, more heavily pre-processed
construction with its own named source and 0-100 (not price-scaled)
output range.

Signal logic
------------
- Long entry: InverseFisher crosses above `long_trigger` (default 12).
- Exit to flat: InverseFisher crosses back below `exit_level` (default
  50), OR a `max_hold_days` time-stop.
- Optional trend filter: close > SMA(trend_window) (this repo's standard
  pattern for oscillator-crossover strategies).
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


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _wma(series: pd.Series, window: int) -> pd.Series:
    weights = np.arange(1, window + 1, dtype=float)
    weight_sum = weights.sum()
    vals = series.to_numpy(dtype=float)
    n = len(vals)
    out = np.full(n, np.nan)
    if n >= window:
        # Vectorized weighted rolling sum via cumulative-sum trick avoided
        # (weights aren't uniform) -- use sliding_window_view for speed
        # instead of pandas rolling().apply() with a Python callback.
        windows = np.lib.stride_tricks.sliding_window_view(vals, window)
        out[window - 1:] = windows @ weights / weight_sum
    return pd.Series(out, index=series.index)


def _rainbow_average(close: pd.Series) -> pd.Series:
    stages = [close]
    for _ in range(9):
        stages.append(_wma(stages[-1], 2))
    weights = [5, 4, 3, 2, 1, 1, 1, 1, 1, 1]
    total = sum(w * s for w, s in zip(weights, stages))
    return total / 20.0


def _rsi(series: pd.Series, window: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _inverse_fisher(close: pd.Series, rsi_period: int, ema_period: int) -> pd.Series:
    rainbow = _rainbow_average(close)
    rsi = _rsi(rainbow, rsi_period)
    x = 0.1 * (rsi - 50)

    ema1 = x.ewm(span=ema_period, adjust=False, min_periods=ema_period).mean()
    ema2 = ema1.ewm(span=ema_period, adjust=False, min_periods=ema_period).mean()
    diff = ema1 - ema2
    z1ema = ema1 + diff

    z1ema_clipped = z1ema.clip(-15, 15)  # avoid overflow in exp()
    inv_fisher = ((np.exp(2 * z1ema_clipped) - 1) / (np.exp(2 * z1ema_clipped) + 1) + 1) * 50
    return inv_fisher


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 4,
    ema_period: int = 4,
    long_trigger: float = 12.0,
    exit_level: float = 50.0,
    trend_window: int = 100,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    inv_fisher = _inverse_fisher(close, rsi_period, ema_period)

    sma_trend = close.rolling(trend_window, min_periods=trend_window).mean()
    above_trend = (close > sma_trend).fillna(False)

    crossed_above_trigger = (inv_fisher > long_trigger) & (inv_fisher.shift(1) <= long_trigger)
    crossed_below_exit = (inv_fisher < exit_level) & (inv_fisher.shift(1) >= exit_level)

    entry_event = crossed_above_trigger.fillna(False) & above_trend
    exit_event = crossed_below_exit.fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_count = 0
    entry_arr = entry_event.values
    exit_arr = exit_event.values

    for i in range(len(df.index)):
        if in_position:
            hold_count += 1
            if exit_arr[i] or hold_count >= max_hold_days:
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
