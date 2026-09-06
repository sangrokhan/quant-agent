"""Strategy: Double ROC (second-derivative momentum acceleration) trend continuation.

Hypothesis (see knowledge_base/strategies_log.jsonl for this run's id):
Per Ocean_Drive's "Double ROC (Acceleration)" TradingView indicator guide
(https://www.tradingview.com/script/1aIO35U8-Double-ROC-Acceleration-by-Ocean-Drive/):
a standard Rate-of-Change (ROC) measures price velocity (first derivative);
taking the ROC of that ROC (via ta.change, NOT a naive percent-change of an
oscillator that crosses zero -- the source explicitly warns this causes
divide-by-zero/distortion) measures acceleration (second derivative). Per
the source's own reading guide: "A cross above the zero line indicates that
upward momentum is accelerating" -- i.e. not just trending, but trending
with increasing velocity, which the source frames as a stronger/more
sustainable signal than a plain ROC/momentum crossover.

Adapted here as a trend-continuation strategy (gated by an existing uptrend
filter so we're not fading -- purely trading acceleration WITHIN a trend,
per the source's own "Trend Exhaustion" caveat about extreme/unsustainable
readings, which we avoid by not shorting the deceleration side):

- Inner ROC: `inner_len`-period rate of change of close (source default 25).
- Outer ROC (acceleration): `outer_len`-period diff of the Inner ROC series
  (source's ta.change(InnerROC, outer_len) -- absolute momentum, not percent).
- Trend filter: close > SMA(`trend_window`) (avoid trading acceleration
  signals against the prevailing trend).
- Entry (long): Outer ROC crosses from <=0 to >0 (acceleration turning
  positive -- source's "upward momentum is accelerating") while in the
  trend filter's uptrend AND Inner ROC > 0 (actual momentum is also
  positive, not just less-negative).
- Exit: Outer ROC crosses back below 0 (deceleration begins -- source's own
  reading rule), OR trend filter breaks (close < SMA), OR a
  `max_hold_days` time-stop.

First second-derivative/acceleration-of-momentum strategy in this repo --
distinct from plain ROC zero-cross (2026-09-04, first-derivative only) and
MACD histogram reversal (2026-09-04, a different acceleration proxy with no
explicit second-ROC construction or divide-by-zero-safe design).

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
    inner_len: int = 25,
    outer_len: int = 25,
    trend_window: int = 100,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    inner_roc = close.pct_change(inner_len) * 100.0
    outer_roc = inner_roc.diff(outer_len)  # ta.change == absolute diff, not pct

    sma = close.rolling(trend_window).mean()
    uptrend = close > sma

    accel_turn_positive = (outer_roc > 0) & (outer_roc.shift(1) <= 0)
    entry = accel_turn_positive & uptrend.fillna(False) & (inner_roc > 0).fillna(False)

    exit_decel = (outer_roc < 0) & (outer_roc.shift(1) >= 0)
    exit_trend_break = ~uptrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_decel.iloc[i]) or bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
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
