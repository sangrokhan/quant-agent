"""Strategy: Monday 2-day-down-streak reversal, signal-based exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-004):
Per QuantifiedStrategies.com's "5 Algorithmic Trading Strategies 2026"
(https://www.quantifiedstrategies.com/algorithmic-trading-strategies/,
Strategy #2, fully disclosed rules): "We buy the S&P 500 at the close on
Monday if the market has closed lower for two consecutive days. We exit
the position when the close rises above the previous day's high." Reported
1993-2026 SPY backtest: 285 trades, 7.7% CAGR, 11% time in market. This is
a distinct combination from every prior day-of-week strategy in this repo:
2026-09-08-116 (Down Monday->Tuesday, single down day, FIXED 1-day hold to
Tuesday's close, no signal-based exit) and 2026-09-08-135 (3-consecutive-day
decline, trades Tue+Wed, signal exit close>yesterday's high). This
strategy uses a 2-day down streak (not 1 or 3) specifically ANCHORED to
Monday (not Tue/Wed), combined with a signal-based exit (not a fixed
next-day hold) -- a new parameter/structure combination not yet tested.

Signal logic
------------
- Entry (long): today is Monday (weekday==0) AND close[today] < close[t-1]
  AND close[t-1] < close[t-2] (2 consecutive down closes ending on Monday).
  Enter at Monday's own close (same-bar entry, matching source's own "buy
  at the close on Monday" rule).
- Exit: close crosses above the previous day's high (source's own stated
  exit trigger), or a max_hold_days safety time-stop (source reports an
  average ~4-day hold with no explicit stop; added purely as a risk
  backstop, consistent with this repo's convention).
- Flat otherwise. No trend filter (source's own rule has none).

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
    down_streak_days: int = 2,
    target_weekday: int = 0,  # 0=Monday
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    n = len(close)

    weekday = pd.Series(df.index.weekday, index=close.index)

    # down streak: close[t] < close[t-1] < ... < close[t-down_streak_days]
    down_day = close < close.shift(1)
    streak_ok = pd.Series(True, index=close.index)
    for k in range(down_streak_days):
        streak_ok &= down_day.shift(k).fillna(False)

    entry_trigger = (weekday == target_weekday) & streak_ok

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    hold_count = 0
    entry_day_idx = None
    for i in range(n):
        if in_position:
            hold_count += 1
            # exit if close crosses above previous day's high
            if i > 0 and close.iloc[i] > high.iloc[i - 1]:
                in_position = False
                hold_count = 0
            elif hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_trigger.iloc[i]:
                in_position = True
                hold_count = 0
                position.iloc[i] = 1  # enter same bar (Monday close)

    return position


def generate_returns(
    price_df: pd.DataFrame,
    down_streak_days: int = 2,
    target_weekday: int = 0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs).

    Position is entered AT the trigger bar's own close (same-bar entry,
    matching the source's "buy at the close on Monday" rule), so the
    return earned on the entry bar itself is zero (no exposure until the
    NEXT bar), and returns from bar t+1 onward use position[t].
    """
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        down_streak_days=down_streak_days,
        target_weekday=target_weekday,
        max_hold_days=max_hold_days,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(float) * daily_returns
    return strat_returns
