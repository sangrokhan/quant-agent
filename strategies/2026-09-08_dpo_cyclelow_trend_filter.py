"""Strategy: DPO cycle-low entry gated by an EMA trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-049):
The Detrended Price Oscillator (DPO) removes the dominant trend from price to
expose short-term cycle position -- DPO(t) = Close[t - (period/2 + 1)] -
SMA(period, t). Per arrowalgo.com's "Cycle timing with a trend filter"
strategy prescription: DPO alone gives no directional signal (explicit
warning against trading it standalone), so combine a DPO extreme-low reading
(price cyclically depressed relative to its recent trend-removed average)
with a trend filter (price above a 50-period EMA) as the entry condition,
and exit when DPO reaches a recurring cyclical high. This is a new indicator
family for this repo (first DPO-based construction) and a distinct
mean-reversion-within-trend construction (cycle position + trend direction)
from the volatility-magnitude and entropy-regularity regime gates already
tested.

Signal logic
------------
- DPO(t) = Close[t - shift] - SMA(dpo_period, t), where shift = dpo_period//2 + 1.
- "Cyclical low" = DPO <= its rolling dpo_lookback-day quantile
  (dpo_low_quantile, e.g. 0.10 -> bottom decile of recent DPO readings).
- "Cyclical high" = DPO >= its rolling dpo_lookback-day quantile
  (dpo_high_quantile, e.g. 0.90 -> top decile).
- Trend filter: close > EMA(trend_ema_window).
- Entry (long): DPO at a cyclical low AND close above the trend EMA.
- Exit: DPO reaches a cyclical high, OR the trend filter flips (close falls
  below the EMA -- risk-off exit), OR after max_hold_days trading days.
- Flat (no position) whenever not in an active long.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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
    dpo_period: int = 20,
    dpo_lookback: int = 126,
    dpo_low_quantile: float = 0.10,
    dpo_high_quantile: float = 0.90,
    trend_ema_window: int = 50,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    shift = dpo_period // 2 + 1
    sma = close.rolling(dpo_period).mean()
    dpo = close.shift(shift) - sma

    dpo_low_thresh = dpo.rolling(dpo_lookback, min_periods=dpo_period).quantile(dpo_low_quantile)
    dpo_high_thresh = dpo.rolling(dpo_lookback, min_periods=dpo_period).quantile(dpo_high_quantile)

    cyclical_low = dpo <= dpo_low_thresh
    cyclical_high = dpo >= dpo_high_thresh

    ema = close.ewm(span=trend_ema_window, adjust=False).mean()
    trend_up = close > ema

    entry = cyclical_low.fillna(False) & trend_up
    exit_cycle_high = cyclical_high.fillna(False)
    exit_trend_flip = ~trend_up

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cycle_high.iloc[i]) or bool(exit_trend_flip.iloc[i]) or held >= max_hold_days:
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
