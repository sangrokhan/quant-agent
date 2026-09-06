"""Strategy: Inside Day Pullback Swing (QuantifiedStrategies "strategy no.3").

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-006):
Per QuantifiedStrategies.com's Inside Day Trading Strategy article
(fully disclosed rule, non-paywalled -- their "strategy no.3" swing
trade): (1) today is an inside day (today's high < yesterday's high AND
today's low > yesterday's low); (2) yesterday's high was below the
previous day's close (i.e. yesterday gapped down / pulled back inside a
prior up-move). If both hold, enter at today's close. Exit when a later
day's close rises above yesterday's high (the pullback's high). Source's
own S&P 500 backtest since 1993: 89 trades, average gain 0.45%/trade,
profit factor 2.1 -- but explicitly "only works in the equity markets...
works opposite in gold". This directly motivates testing it against BOTH
equity and crypto per this repo's standard grid, expecting the crypto leg
to fail or invert (consistent with the source's own gold counter-example
suggesting the edge is equity-specific, not a universal micro-structure
effect).

This is distinct from the already-tested Inside Bar breakout
(2026-09-04 inside_bar_breakout_trend.py, EMA-trend-filtered breakout
ABOVE the mother bar's high) because this is a mean-reversion / pullback
continuation trade that enters at today's close on the inside day itself
(no waiting for a breakout), gated by a specific PRIOR-DAY gap-down
condition (yesterday's high < day-before's close) rather than an EMA
trend filter, with exit defined purely by price recovering above
yesterday's high (no time-stop in the source's own rule, though a
max_hold_days safety backstop is added here per this repo's standard
practice to avoid unbounded holds).

Signal logic
------------
- Inside day: high[t] < high[t-1] AND low[t] > low[t-1].
- Yesterday gapped down vs the day before: high[t-1] < close[t-2].
- Entry (long): both conditions true on day t, enter at close[t].
- Exit: close[t] > high[t-1] (source's own rule: today's close exceeds
  the pullback day's high) evaluated on each subsequent day using the
  ORIGINAL entry day's high[t-1] as the target, OR a max_hold_days
  safety time-stop (source didn't specify one, standard repo practice).
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
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close, high, low = df["close"], df["high"], df["low"]

    inside_day = (high < high.shift(1)) & (low > low.shift(1))
    gapped_down_prior = high.shift(1) < close.shift(2)
    entry = (inside_day & gapped_down_prior).fillna(False)

    high_arr = high.to_numpy()
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
                target_high = high_shift1_arr[i]  # yesterday's high (pullback target)
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    max_hold_days: int = 15,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(price_df, max_hold_days=max_hold_days)
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
