"""Strategy: Breakaway gap continuation (long-only, volume-confirmed).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-025):
Per quantifiedstrategies.com's "Breakaway Gaps: Definition And Trading
Strategy Example With Backtest and Trading Rules" (visited this iteration
via browser_exec after web_extract errored -- ddgs backend is search-only):
a breakaway gap is a price move that "opens above yesterday's high and
never trades below yesterday's high," typically accompanied by above-
average volume, signaling the potential start of a new trend (as opposed to
a runaway/exhaustion/common gap). The source's own disclosed backtest
methodology tests a fixed N-trading-day time stop (1 to 10 days) on GLD, and
explicitly reports the standalone-gap version gives "pretty random results"
on both GLD and other assets, with a 3-rule combined version ("number of
trades goes down, but average gain improves") performing better -- though
the article does not fully spell out rules 2 and 3's exact numeric
thresholds in the visible extracted text (placeholder text "you find the
trading rules at the bottom of the article" recurs without the actual
numbers rendering), so this repo's implementation operationalizes the
disclosed CORE definition (gap opens above yesterday's high, closes above
yesterday's high all session, above-average volume) plus a standard
N-day time-stop, rather than inventing the undisclosed rules 2/3 from
model recall.

First breakaway-gap-specific strategy in this repo (0 prior hits in
strategies_index.jsonl for "breakaway gap") -- distinct from already-tested
generic gap strategies (weekday-gap-continuation, gap-down-fade, Bullish
Island Reversal) since this requires the SPECIFIC breakaway-gap
qualification (gap fully clears yesterday's high with no intraday trade
below it) plus a volume-surge confirmation, not just any positive
overnight gap.

Interface contract (see validation/validators.py / validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
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
    vol_mult: float = 1.5,       # today's volume >= vol_mult x its own rolling avg
    vol_avg_window: int = 20,
    time_stop_days: int = 5,     # source tested 1-10 day time stops
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]

    prior_high = h.shift(1)
    prior_low = l.shift(1)
    avg_vol = v.rolling(vol_avg_window).mean()

    # Breakaway gap qualification (per source's own core definition):
    # opens above yesterday's high AND never trades below yesterday's high
    # during the session (low stays above prior high) -- plus volume surge.
    gap_up = o > prior_high
    holds_above = l >= prior_high
    vol_confirm = v >= (vol_mult * avg_vol)

    breakaway_gap = gap_up & holds_above & vol_confirm.fillna(False)

    position = pd.Series(0, index=c.index, dtype=int)
    in_position = False
    entry_idx = 0
    n = len(c)
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if held >= time_stop_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(breakaway_gap.iloc[i]):
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
