"""Strategy: Combined multi-pattern bearish-named candlestick mean-reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-21-269):
Per QuantifiedStrategies.com's "Candlestick Patterns That Actually Work:
Ranked by Backtested Performance"
(https://quantifiedstrategies.substack.com/p/candlestick-patterns-that-actually),
a systematic 75-pattern SPY backtest (1993-present) found several patterns
with "bearish" names (Bearish Engulfing #1, Three Outside Down #2, Dark
Cloud Cover #3) plus bullish-reversal patterns (Bullish Piercing Line #4,
Three Inside Up #5) actually function as BULLISH mean-reversion signals in
equities (source's own explanation: stocks mean-revert more reliably than
forex/crypto). The source's own headline result came not from any single
pattern but from COMBINING the top patterns into one OR-gated entry rule
with a MODIFIED exit (close above prior day's high, not a fixed holding
period) -- reported net profit 1,320% / win rate 74% / CAGR 8.3% / MDD 13%
on SPY 1993-2026 with 0.03% costs. Every individual pattern in this list
(Three Outside Down, Dark Cloud Cover, Bullish Harami, Three Inside Up) has
already been tested standalone in this repo and rejected -- this iteration
tests the COMBINED multi-pattern OR-gate + modified-exit construction
specifically, which is a distinct technique (0 prior "combined candlestick"
KB hits) even though the individual pattern definitions are not new.
Uses the top-5-ranked patterns from the source (Bearish Engulfing, Three
Outside Down, Dark Cloud Cover, Bullish Piercing Line, Three Inside Up) as
the combined signal set, since the source's article names its overall #1-5
ranking but does not explicitly enumerate which "five best" patterns went
into the combined test -- this is the best-supported reconstruction from
the disclosed ranking.

Signal logic
------------
Long entry (any OR-gated pattern confirmed at today's close):
  - Bearish Engulfing: yesterday bullish body, today bearish body that
    fully engulfs yesterday's body (today open > yesterday close, today
    close < yesterday open).
  - Three Outside Down: day1 bullish, day2 bearish-engulfs day1, day3
    closes below day2's close (confirmation).
  - Dark Cloud Cover: day1 long bullish candle, day2 opens above day1's
    high (gap up) and closes below the midpoint of day1's body.
  - Bullish Piercing Line: day1 bearish candle, day2 opens below day1's
    low and closes above the midpoint of day1's body (but below day1's
    open).
  - Three Inside Up: day1 bearish, day2 bullish harami (body inside day1's
    body), day3 closes above day2's close (confirmation).
Exit: close crosses above the PRIOR day's high (source's own modified exit
rule), OR a max_hold_days time-stop fallback (source used a pure
close>prior-high exit with no time-stop; we add one as this repo's standard
safety net against indefinite holds).
Flat otherwise; no shorting (all signals are long-only mean-reversion, per
the source's finding).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _combined_pattern_signal(df: pd.DataFrame) -> pd.Series:
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    o1, c1, h1, l1 = o.shift(1), c.shift(1), h.shift(1), l.shift(1)
    o2, c2 = o.shift(2), c.shift(2)

    day1_bullish = c1 > o1
    day1_bearish = c1 < o1
    today_bullish = c > o
    today_bearish = c < o

    # Bearish Engulfing (today engulfs yesterday's bullish body)
    bearish_engulfing = day1_bullish & today_bearish & (o > c1) & (c < o1)

    # Three Outside Down: day-2 bullish, day-1 bearish-engulfs day-2, today closes lower
    d2_bullish = c2 > o2
    d1_engulfs_d2 = (c1 < o1) & (o1 > c2) & (c1 < o2)
    three_outside_down = d2_bullish & d1_engulfs_d2 & (c < c1)

    # Dark Cloud Cover: yesterday long bullish, today gaps above yesterday's high
    # and closes below the midpoint of yesterday's body
    y_mid = (o1 + c1) / 2.0
    dark_cloud_cover = day1_bullish & (o > h1) & (c < y_mid) & (c > o1)

    # Bullish Piercing Line: yesterday bearish, today opens below yesterday's low,
    # closes above yesterday's body midpoint but below yesterday's open
    piercing_line = day1_bearish & (o < l1) & (c > y_mid) & (c < o1)

    # Three Inside Up: day-2 bearish, day-1 bullish harami inside day-2's body,
    # today closes above day-1's close (confirmation)
    d2_bearish = c2 < o2
    d1_harami = (c1 > o1) & (o1 >= c2) & (c1 <= o2)
    three_inside_up = d2_bearish & d1_harami & (c > c1)

    combined = (
        bearish_engulfing
        | three_outside_down
        | dark_cloud_cover
        | piercing_line
        | three_inside_up
    )
    return combined.fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    max_hold_days: int = 15,
    min_hold_days: int = 1,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    ``min_hold_days`` (added in the 2026-09-21-270 near-miss rescue of
    2026-09-21-269): ignore the exit signal for the first N days after
    entry, to cut round-trip trade count/turnover (the near-miss's failure
    mode was transaction-cost-survival from high turnover, not raw edge).
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]

    entry_signal = _combined_pattern_signal(df)
    exit_signal = close > high.shift(1)

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    hold_bars = 0
    for i in range(len(close)):
        if in_pos:
            hold_bars += 1
            exit_allowed = hold_bars >= min_hold_days
            if (exit_allowed and bool(exit_signal.iloc[i])) or hold_bars >= max_hold_days:
                in_pos = False
                hold_bars = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
                in_pos = True
                hold_bars = 0
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    max_hold_days: int = 15,
    min_hold_days: int = 1,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, max_hold_days=max_hold_days, min_hold_days=min_hold_days)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
