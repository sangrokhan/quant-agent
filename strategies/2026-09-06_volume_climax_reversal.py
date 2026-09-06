"""Strategy: Volume Climax Reversal (long side).

Hypothesis (see knowledge_base/strategies_log.jsonl for this run's id):
Per Finveroo's "Volume Climax Reversal Strategy" guide
(https://www.finveroo.com/trading-academy/strategies/volume/volume-climax/):
an extended downtrend that ends in a volume spike (volume >> recent average)
occurring on a new N-day low, followed immediately by a rejection candle
(long lower wick, close in the upper portion of the day's range) signals
exhaustion of sellers and a probable reversal. Adapted to daily OHLCV bars
(source's own "15m/1h/4h" note is time-frame-agnostic in principle -- the
climax+rejection logic doesn't depend on bar size):

- "Extended move": close made a new `lookback_window`-day low.
- "Volume spike": volume >= `vol_mult` * rolling average volume
  (`vol_avg_window` days, excluding the spike day itself).
- "Rejection candle" (source's Step 3): lower wick ratio
  (min(open,close) - low) / (high - low) >= `wick_ratio_threshold`, AND
  close is in the upper half of the day's range (close > (high+low)/2).
- Entry: long at the close of the day the above three conditions all hold
  (source's Step 5 "enter on the candle close that confirms the rejection").
  This repo's generate_returns() shifts position by 1 day before applying
  returns, so the position is effectively taken by next day's open/close.
- Exit (source's Step 4/7, simplified since no explicit structure-break
  detector exists in this repo yet): close breaking back above the
  `exit_sma_window`-day SMA (a proxy for "reversal confirmed, momentum
  resuming upward"), OR a `max_hold_days` time-stop (source doesn't specify
  a hard time exit, but this repo's convention avoids indefinite holds).

This is the first volume-spike-driven reversal strategy in this repo --
distinct from RVOL breakout confirmation (2026-09-04, trend CONTINUATION
after a volume spike, not reversal) and RSI high-volume capitulation
(2026-09-05, RSI-driven not wick/candle-shape-driven).

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
    lookback_window: int = 20,
    vol_avg_window: int = 20,
    vol_mult: float = 3.0,
    wick_ratio_threshold: float = 0.5,
    exit_sma_window: int = 10,
    max_hold_days: int = 8,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]

    new_low = c <= c.rolling(lookback_window).min()
    avg_vol = v.rolling(vol_avg_window).mean().shift(1)
    vol_spike = v >= (vol_mult * avg_vol)

    rng = (h - l).replace(0, pd.NA)
    lower_wick_ratio = ((o.where(o < c, c) - l) / rng).astype(float)
    upper_half_close = c > ((h + l) / 2.0)
    rejection_candle = (lower_wick_ratio >= wick_ratio_threshold) & upper_half_close

    entry = new_low & vol_spike.fillna(False) & rejection_candle.fillna(False)

    sma_exit = c.rolling(exit_sma_window).mean()
    exit_meanrev = c > sma_exit

    position = pd.Series(0, index=c.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(c)):
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
