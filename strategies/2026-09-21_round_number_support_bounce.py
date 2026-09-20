"""Strategy: Round-number psychological support bounce, gated by an uptrend
filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-172):
A well-documented market microstructure phenomenon (Donaldson & Kim 1993,
"Price Barriers in the Dow Jones Industrial Average", and the broader
"psychological round-number level" literature -- the primary academic
source paper itself was captcha-blocked on ScienceDirect this iteration,
but the underlying concept is corroborated across multiple independent
technical-analysis education sources found via browser_exec search) holds
that round numbers (multiples of a price's own natural round-number
increment, e.g. every $5 or $10 for a security trading in the hundreds)
act as psychological support/resistance because limit orders and
round-number-anchored decision-making cluster there. This strategy
operationalizes the SUPPORT side (bullish bounce off a round number from
above, in an established uptrend) as a mechanical, testable rule: 0 prior
round-number/psychological-level entries in this repo.

Signal logic
------------
- Round-number grid: `round_increment` (a price level like 5.0 or 10.0,
  scaled by `round_increment_pct` of the current price if
  `adaptive_increment=True` so the grid stays meaningful across different
  price regimes over a multi-year sample, e.g. QQQ near $600 uses a
  bigger increment than QQQ near $150).
- Nearest round level below today's low: `floor(low / increment) * increment`.
- Entry (long): the low of the bar comes within `touch_pct` of that
  nearest-round-level-below (a "touch" of the round number from above)
  AND the bar's close finishes back above the round level (rejection off
  support, not a breakdown) AND close > SMA(trend_window) (uptrend
  context -- per the literature, round-number support bounces are more
  reliable with the trend, not as a standalone reversal tool).
- Exit: close falls below the SAME round level (support genuinely
  breaks), OR max_hold_days reached, whichever first.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position series)
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    round_increment_pct: float = 0.02,
    touch_pct: float = 0.005,
    trend_window: int = 100,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    idx = df.index
    n = len(idx)

    close = df["close"]
    low = df["low"]
    trend_sma = close.rolling(trend_window).mean()

    position = pd.Series(0, index=idx, dtype=int)
    in_position = False
    entry_i = -1
    support_level = None

    for i in range(n):
        px = close.iloc[i]
        increment = max(px * round_increment_pct, 1e-9)

        if in_position:
            hold_days = i - entry_i
            support_break = close.iloc[i] < support_level
            if support_break or hold_days >= max_hold_days:
                in_position = False
                support_level = None
            else:
                position.iloc[i] = 1
        else:
            round_below = math.floor(low.iloc[i] / increment) * increment
            touched = (low.iloc[i] - round_below) <= touch_pct * increment
            rejected = close.iloc[i] > round_below
            trend_ok = pd.notna(trend_sma.iloc[i]) and close.iloc[i] > trend_sma.iloc[i]
            if touched and rejected and trend_ok and round_below > 0:
                in_position = True
                entry_i = i
                support_level = round_below
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    round_increment_pct: float = 0.02,
    touch_pct: float = 0.005,
    trend_window: int = 100,
    max_hold_days: int = 15,
) -> pd.Series:
    """Daily strategy returns (no transaction costs applied here)."""
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        round_increment_pct=round_increment_pct,
        touch_pct=touch_pct,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
