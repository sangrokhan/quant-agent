"""Strategy: Classic Floor-Trader Pivot Point "S1 Bounce" mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-07-025):
Per ArrowAlgo's "Pivot Point Trading Strategy" guide's disclosed "S1
Bounce (Mean Reversion)" rule (Google search-result snippet, corroborated
by a UNIVPM academic thesis's own pseudo-code reference to a "BreakP_Long"
/ S1-bounce variant of the classic pivot-point strategy family): using
the classic floor-trader daily pivot formula (P=(prior H+L+C)/3,
S1=2P-prior_H, R1=2P-prior_L), a long entry triggers when price touches
or dips to/below S1 intraday (low <= S1) and then closes back above S1 on
the SAME bar (source's own filter: "only take the trade when" price
recovers within the bar, not merely closing below S1 and drifting).
Exit at the pivot point P itself (the natural first target above S1,
per the source's stop/target framing) or a max_hold_days time-stop
backstop.

This is distinct from the two other pivot-point strategies already
tested in this repo: 2026-09-04-073 (a BREAKOUT variant -- close crossing
ABOVE P/R1/S1 signals a new uptrend, opposite economic logic from a
bounce/mean-reversion trade at S1) and 2026-09-04-119 (Camarilla pivot
points, a DIFFERENT formula entirely with 8 levels and a 1.1
Fibonacci-derived multiplier, entering at S3-equivalent not the classic
S1). This is the first CLASSIC floor-trader S1-bounce mean-reversion
strategy in this repo.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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
    max_hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    prior_high = high.shift(1)
    prior_low = low.shift(1)
    prior_close = close.shift(1)

    pivot = (prior_high + prior_low + prior_close) / 3.0
    s1 = 2 * pivot - prior_high

    # S1 Bounce entry: today's LOW touches/dips to or below S1, but today's
    # CLOSE recovers back above S1 (same-bar recovery filter per source).
    touched_s1 = low <= s1
    closed_above_s1 = close > s1
    entry = (touched_s1 & closed_above_s1).fillna(False)

    # Exit target: close recovers to/above the pivot point P itself.
    exit_target = close >= pivot

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    hold_count = 0
    for i in range(len(close)):
        if in_position:
            hold_count += 1
            if bool(exit_target.iloc[i]) or hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                hold_count = 0
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
