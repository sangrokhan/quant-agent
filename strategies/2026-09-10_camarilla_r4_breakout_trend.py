"""Strategy: Camarilla Pivot R4 breakout trend-continuation (long-only).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-124):
Per a Google AI-overview synthesis (Medium/Bhaskar Das et al) via
browser_exec Google SERP fallback of "Camarilla pivot points daily trading
strategy": the Camarilla pivot system's own stated rule distinguishes R3/S3
(major reversal/zone-boundary levels, where price "usually stops and turns
back toward the center" -- used for range-bound mean reversion) from R4/S4
("extreme boundary lines... breaking past these signals a powerful new
directional trend" -- used for breakout/trend-continuation trades). This
repo already tested the R3/S3 reversal-zone mean-reversion variant
(2026-09-04-119: long when close dips below prior-day S3 but stays above
S4, exit at R1). This strategy tests the OPPOSITE, breakout-mechanic half
of the same indicator system that the source itself calls out as distinct:
long entry when close breaks ABOVE the prior day's R4 level (confirmed
directional-trend breakout), exit when close falls back below the prior
day's pivot (P) or R3 level, or after a max holding period.

Camarilla levels (anchored on the PRIOR session's H/L/C, per Nick Scott's
1989 formula, camarilla_mult default 1.1/12 Fibonacci-derived constant):
  range = prior_high - prior_low
  R4 = prior_close + range * camarilla_mult * (4/2)   # extreme resistance
  R3 = prior_close + range * camarilla_mult * (3/4)   # major resistance
  P  = (prior_high + prior_low + prior_close) / 3      # central pivot

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
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


def _camarilla_levels(df: pd.DataFrame, camarilla_mult: float = 1.1):
    prior_high = df["high"].shift(1)
    prior_low = df["low"].shift(1)
    prior_close = df["close"].shift(1)
    rng = prior_high - prior_low

    r4 = prior_close + rng * camarilla_mult * (4.0 / 2.0)
    r3 = prior_close + rng * camarilla_mult * (3.0 / 4.0)
    pivot = (prior_high + prior_low + prior_close) / 3.0
    return r4, r3, pivot


def generate_signals(
    price_df: pd.DataFrame,
    camarilla_mult: float = 1.1,
    exit_level: str = "pivot",  # "pivot" or "r3"
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    r4, r3, pivot = _camarilla_levels(df, camarilla_mult)
    exit_line = pivot if exit_level == "pivot" else r3

    entry = (close > r4) & r4.notna()
    exit_break = (close < exit_line) & exit_line.notna()

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_break.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
