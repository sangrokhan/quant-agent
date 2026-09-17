"""Strategy: Three-Line Break (Sanbon Kaiten) chart reversal, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-031):
Per adigitalblogger.com's "Three Line Break Chart" explainer
(https://www.adigitalblogger.com/charts/three-line-break-chart/, visited
this iteration via browser_exec after a Google SERP search -- web_search
DDGS backend unreliable this trigger), the Three-Line-Break chart (18th
century Japanese "Sanbon Kaiten", popularized in the US by Steve Nison's
"Beyond Candlesticks") builds a sequence of up/down blocks purely from
closing prices, ignoring time and intraday range:

- A new UP block forms whenever the close exceeds the high of the current
  block (extending the current up-run, or starting a fresh up-run).
- A new DOWN block forms whenever the close falls below the low of the
  current block.
- A REVERSAL only occurs when the close breaks beyond the high/low of the
  PREVIOUS `n_lines` (source: 3) blocks in the opposite direction of the
  current trend -- not just the single most recent block. This is the
  chart's defining "three line break" rule: you need a decisive move past
  3 blocks' worth of extreme to flip.
- Source's own disclosed trading rule: "buy when a white [up] line comes up
  after 3 consecutive black [down] lines, and sell when a black line comes
  up after 3 consecutive white lines" -- i.e. trade the reversal itself,
  not every same-direction continuation block.

This repo has zero prior Three-Line-Break entries -- distinct from Renko
(fixed brick size) and Point & Figure (box+reversal on a price grid) chart
constructions already tested, since 3LB's reversal threshold is dynamically
defined by the actual high/low of the last N blocks (self-adjusting to
recent volatility) rather than a fixed box/brick size.

Signal logic (long-only daily-bar adaptation)
------------------------------------------------
- n_lines: number of trailing same-direction blocks required to break
  through before a reversal counts (source's disclosed default: 3).
- Block construction: maintain a rolling list of blocks (direction, high,
  low) built from daily closes per the up/down/reversal rules above.
- Long entry: an UP-direction reversal block forms after >= n_lines
  consecutive DOWN blocks (a decisive break above the extreme high of the
  last n_lines down-blocks).
- Exit: a DOWN-direction reversal block forms (>= n_lines consecutive UP
  blocks broken), or a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py) and
grid_test.py: generate_signals/generate_returns take price_df plus keyword
params.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _three_line_break_signals(closes: np.ndarray, n_lines: int) -> np.ndarray:
    """Build the 3LB block sequence from closes and flag reversal bars.

    Returns an array of ints per bar: +1 = bullish reversal just confirmed
    on this bar, -1 = bearish reversal just confirmed, 0 = no reversal
    (continuation or no new block).
    """
    n = len(closes)
    reversal_flag = np.zeros(n, dtype=int)
    if n == 0:
        return reversal_flag

    # blocks: list of (direction, high, low); direction +1 up, -1 down
    blocks: list[tuple[int, float, float]] = []
    blocks.append((0, closes[0], closes[0]))  # seed block, neutral

    for i in range(1, n):
        c = closes[i]
        cur_dir, cur_high, cur_low = blocks[-1]

        if cur_dir >= 0:
            # currently up (or seed) -- check for new up block or reversal down
            if c > cur_high:
                blocks.append((1, c, cur_low if cur_dir == 1 else c))
                # continuation up, no reversal flag
            else:
                # check reversal down: need close below the low of the last n_lines blocks
                lookback = blocks[-n_lines:] if len(blocks) >= n_lines else blocks
                extreme_low = min(b[2] for b in lookback)
                # require at least n_lines consecutive up blocks (or seed+up) before reversal counts
                up_run = 0
                for b in reversed(blocks):
                    if b[0] == 1:
                        up_run += 1
                    else:
                        break
                if c < extreme_low and up_run >= n_lines:
                    blocks.append((-1, c, c))
                    reversal_flag[i] = -1
                # else: no new block, price sits inside range -- carry state forward
        else:
            # currently down -- check for new down block or reversal up
            if c < cur_low:
                blocks.append((-1, cur_high, c))
            else:
                lookback = blocks[-n_lines:] if len(blocks) >= n_lines else blocks
                extreme_high = max(b[1] for b in lookback)
                down_run = 0
                for b in reversed(blocks):
                    if b[0] == -1:
                        down_run += 1
                    else:
                        break
                if c > extreme_high and down_run >= n_lines:
                    blocks.append((1, c, c))
                    reversal_flag[i] = 1

    return reversal_flag


def generate_signals(
    price_df: pd.DataFrame,
    n_lines: int = 3,
    max_hold_days: int = 25,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    closes = df["close"].to_numpy(dtype=float)
    reversal = _three_line_break_signals(closes, n_lines)

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            if reversal[i] == -1 or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if reversal[i] == 1:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    n_lines: int = 3,
    max_hold_days: int = 25,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(df, n_lines=n_lines, max_hold_days=max_hold_days)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
