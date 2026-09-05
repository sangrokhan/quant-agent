"""Strategy: Dual-EMA trend-filtered Moving Average Envelope breakout,
long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-096),
sourced from a Google AI-overview synthesis (queried "Envelope channel
dual moving average breakout strategy specific numeric rules ATR"):
"Fast Moving Average (FMA): 20-period EMA. Slow Moving Average: 50-period
EMA. Envelope Baseline: 20-period SMA. Envelope Distance: 2.0% band shift
from the baseline... Long Entry: Trend Filter: 20 EMA > 50 EMA. Trigger:
the current bar's closing price must cross and close above the Upper
Envelope Line."

Distinct from this repo's already-tested plain Moving Average Envelope
strategy (2026-09-04-065, rejected decisively 0/36 grid cells) which was
a MEAN-REVERSION variant (buy on a touch of the LOWER envelope band, no
trend filter at all). This is the opposite trigger direction (BREAKOUT
above the UPPER band) combined with a dual-EMA(20/50) trend-alignment
gate that the earlier variant entirely lacked -- the trend filter should
screen out breakouts that occur against the prevailing medium-term trend,
addressing a likely cause of the earlier variant's failure (whipsaw
entries in non-trending conditions).

Signal logic
------------
- Envelope baseline = SMA(close, envelope_window); band shift =
  envelope_pct (e.g. 0.02 = 2%).
- Upper envelope = baseline * (1 + envelope_pct).
- Trend filter: EMA(close, fast_span) > EMA(close, slow_span).
- Long entry: trend filter true AND close crosses above the upper
  envelope band (close[t-1] <= upper[t-1], close[t] > upper[t]).
- Exit: close crosses back below the envelope baseline (SMA), OR the
  trend filter breaks (fast EMA <= slow EMA), OR a max_hold_days
  time-stop (repo standard safety valve).

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns, position lagged by 1 day to avoid look-ahead bias)
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
    envelope_window: int = 20,
    envelope_pct: float = 0.02,
    fast_span: int = 20,
    slow_span: int = 50,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    baseline = close.rolling(envelope_window).mean()
    upper = baseline * (1 + envelope_pct)

    ema_fast = close.ewm(span=fast_span, adjust=False, min_periods=fast_span).mean()
    ema_slow = close.ewm(span=slow_span, adjust=False, min_periods=slow_span).mean()
    trend_up = ema_fast > ema_slow

    crossed_up = (close > upper) & (close.shift(1) <= upper.shift(1))
    entry_signal = (crossed_up & trend_up).fillna(False).values

    crossed_down_baseline = (close < baseline) & (close.shift(1) >= baseline.shift(1))
    trend_break = ~trend_up
    exit_signal = (crossed_down_baseline | trend_break).fillna(False).values

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_count = 0

    for i in range(len(df.index)):
        if in_position:
            hold_count += 1
            if exit_signal[i] or hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_signal[i]:
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
