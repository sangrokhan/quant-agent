"""Strategy: Inside Day Pullback Swing + 200d SMA Trend Gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-007):
Direct follow-up to near-miss 2026-09-07-006 (Inside Day Pullback Swing,
QQQ Sharpe 0.651 / SPY Sharpe 0.716, both below the 1.0 threshold, but
MDD/transaction-cost/parameter-sensitivity ALL passed comfortably). That
strategy's own backtest report flagged this exact follow-up: add a 200-day
SMA uptrend gate (this repo's most common successful filter, e.g.
2026-09-03-021 SMA(50)>SMA(200) vol-gated, 2026-09-04-089 IBS+SMA-band)
to filter OUT counter-trend inside-day pullbacks, hypothesizing that the
setup's edge is concentrated in established uptrends (consistent with
this repo's broad empirical finding that trend/momentum/mean-reversion
setups alike tend to only show a real edge above the 200d SMA).

Identical entry/exit mechanism to 2026-09-07-006 (inside day + prior
day gapped down vs 2-days-ago close -> enter at close; exit on close
exceeding the pullback day's high, or max_hold_days time-stop), with
ONE added condition: only enter when close > SMA(trend_window) at the
time of entry.

Signal logic
------------
- Inside day: high[t] < high[t-1] AND low[t] > low[t-1].
- Yesterday gapped down vs the day before: high[t-1] < close[t-2].
- Trend filter: close[t] > SMA(trend_window)[t].
- Entry (long): inside day AND gap-down-pullback AND trend filter, all on
  day t -> enter at close[t].
- Exit: close > target_high (yesterday's high at entry time), OR
  max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and
grid_test.py: generate_signals/generate_returns take price_df plus keyword
params.
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
    max_hold_days: int = 15,
    trend_window: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close, high, low = df["close"], df["high"], df["low"]

    inside_day = (high < high.shift(1)) & (low > low.shift(1))
    gapped_down_prior = high.shift(1) < close.shift(2)
    trend_sma = close.rolling(trend_window).mean()
    uptrend = close > trend_sma

    entry = (inside_day & gapped_down_prior & uptrend).fillna(False)

    high_shift1_arr = high.shift(1).to_numpy()
    close_arr = close.to_numpy()
    entry_arr = entry.to_numpy()

    position = pd.Series(0, index=df.index, dtype=int)
    pos_arr = position.to_numpy().copy()

    in_pos = False
    hold_counter = 0
    target_high = None

    for i in range(len(df)):
        if in_pos:
            hold_counter += 1
            if close_arr[i] > target_high or hold_counter >= max_hold_days:
                in_pos = False
                hold_counter = 0
                target_high = None
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if entry_arr[i]:
                in_pos = True
                hold_counter = 0
                target_high = high_shift1_arr[i]
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    max_hold_days: int = 15,
    trend_window: int = 200,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        price_df, max_hold_days=max_hold_days, trend_window=trend_window
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
