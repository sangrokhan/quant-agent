"""Strategy: Three Line Break (3LB) trend-reversal signal.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-040):
Three Line Break charts (originated in Japan, per StockCharts ChartSchool
https://chartschool.stockcharts.com/table-of-contents/chart-analysis/chart-types/three-line-break-charts)
plot closing-price-based "lines" (white=up, black=down): a new line of the
SAME color is drawn every time price extends beyond the current line's
extreme in the trend direction (no threshold needed); a new line of the
OPPOSITE color (a reversal) is only drawn when price closes beyond the
high/low of the prior `reversal_lines` lines (the source's "two-line
reversal" rule: for a down-trend, the reversal point is the high of the
last two lines; the mirror rule applies to up-trends). A stronger
"Three Line Break" signal specifically requires N (default 3) consecutive
same-color lines before the single opposite-color break -- StockCharts
frames this as signalling a genuine trend reversal rather than a
transient 2-line pullback. This strategy reconstructs that line sequence
directly from daily closes (each new same-direction extreme = one line;
`run_len` = number of consecutive same-color lines completed so far in
the current run) and goes long on a bullish N-line break (>= break_n_lines
down-lines broken to the upside), flat/exit on ANY down-reversal (matching
the source's own asymmetric weak-2-line/strong-N-line framing -- exit is
more conservative/faster than entry) or a max_hold_days time-stop.
Distinct from the already-tested Renko (fixed ATR-box grid, rejected
2026-09-04-086/087) and Point & Figure (fixed box + fixed reversal-count
grid, accepted 2026-09-04-143) constructions -- 3LB's reversal threshold
is the dynamic range of the prior LINES themselves (which can span any
number of calendar days each), with no fixed box size at all.

Signal logic
------------
- Reconstruct closes into a 3LB line sequence: track the current run's
  color and a `run_history` list of successive extremes (a new entry is
  appended each time price sets a fresh extreme in the trend direction --
  each entry = one "line"). A reversal to the opposite color occurs when
  price closes beyond the extreme reached `reversal_lines` lines back in
  the run history (default 2, i.e. the standard "two-line reversal" rule).
- `run_len` = number of lines in the run that just completed (length of
  `run_history` at the moment of reversal).
- Entry (long): reversal to an up-line, and the completed down-run had
  run_len >= break_n_lines (the strong "N-line break" bullish signal).
- Exit: any reversal to a down-line, or a max_hold_days time-stop.
- Flat otherwise (long-only; no short leg per SAFETY.md scope).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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
    reversal_lines: int = 2,  # standard "two-line reversal" threshold
    break_n_lines: int = 3,   # N consecutive same-color lines needed for a "strong" break signal
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series based on Three Line Break reversals."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    position = pd.Series(0, index=close.index, dtype=int)

    cur_color = None  # "W" (up) or "B" (down)
    # run_history[0] = the level where the current run began (the reversal
    # point that started it); run_history[-1] = current running extreme.
    # len(run_history) - 1 == number of lines completed so far in this run.
    run_history: list = []

    in_position = False
    entry_idx = 0

    warmup = 3
    for i in range(n):
        price = close.iloc[i]

        if i < warmup:
            position.iloc[i] = 1 if in_position else 0
            continue

        flipped_to_white = False
        flipped_to_black = False
        completed_run_len = 0

        if cur_color is None:
            cur_color = "W" if price >= close.iloc[0] else "B"
            run_history = [close.iloc[0], price] if price != close.iloc[0] else [close.iloc[0]]
        else:
            cur_extreme = run_history[-1]
            if cur_color == "W":
                if price > cur_extreme:
                    run_history.append(price)  # new same-color line
                else:
                    idx = len(run_history) - 1 - reversal_lines
                    reversal_pt = run_history[idx] if idx >= 0 else run_history[0]
                    if price < reversal_pt:
                        completed_run_len = len(run_history) - 1
                        cur_color = "B"
                        run_history = [cur_extreme, price]
                        flipped_to_black = True
            else:  # "B"
                if price < cur_extreme:
                    run_history.append(price)
                else:
                    idx = len(run_history) - 1 - reversal_lines
                    reversal_pt = run_history[idx] if idx >= 0 else run_history[0]
                    if price > reversal_pt:
                        completed_run_len = len(run_history) - 1
                        cur_color = "W"
                        run_history = [cur_extreme, price]
                        flipped_to_white = True

        entry_signal = flipped_to_white and completed_run_len >= break_n_lines
        exit_signal = flipped_to_black

        if in_position:
            held = i - entry_idx
            if exit_signal or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if entry_signal:
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
