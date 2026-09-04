"""Strategy: Camarilla Pivot Points (Nick Scott, 1989) daily mean-reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-119):
Camarilla pivot points, derived from the PRIOR day's (H,L,C), use a
Fibonacci-derived 1.1 multiplier to compute 8 support/resistance levels
anchored around the previous close. Source (stockgro.club) states the
core premise: unless a confirmed breakout past R4/S4 occurs, price tends
to mean-revert toward the close-anchored zone during the session -- R3/S3
are described as the "most actively watched reversal zones" (overbought/
oversold). We implement a daily-bar long-only mean-reversion rule: enter
long when today's close dips below yesterday's S3 level (oversold zone,
analogous to the worked example's "bounce at S3"), exit when close
recovers back above the pivot's R1 level (first target per the source's
"target R1 and R2 progressively"), or a max_hold_days time-stop. We
additionally gate out entries where the close has already broken decisively
below S4 (a "confirmed breakdown", per the source's own caveat that mean
reversion doesn't hold through a genuine breakout).

Formula (levels computed from PRIOR trading day's H, L, C, shifted so no
look-ahead)
------------------------------------------------------------------------
range = H - L
R1 = C + range * 1.1 / 12      S1 = C - range * 1.1 / 12
R3 = C + range * 1.1 / 4       S3 = C - range * 1.1 / 4
R4 = C + range * 1.1 / 2       S4 = C - range * 1.1 / 2

Signal logic
------------
- Entry (long): close < S3 (of the prior day) AND close > S4 (not a
  confirmed breakdown past the outer band).
- Exit: close > R1 (first target reached), OR max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept params as keyword args.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _camarilla_levels(df: pd.DataFrame, entry_divisor: float, exit_divisor: float):
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)

    # Use PRIOR bar's H/L/C (shift by 1) so today's entry decision never
    # looks ahead at today's own high/low/close.
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)
    rng = prev_high - prev_low

    exit_level = prev_close + rng * 1.1 / exit_divisor
    entry_level = prev_close - rng * 1.1 / entry_divisor
    s4 = prev_close - rng * 1.1 / 2
    return exit_level, entry_level, s4


def generate_signals(
    price_df: pd.DataFrame,
    entry_divisor: float = 4.0,
    exit_divisor: float = 12.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    ``entry_divisor``=4.0 -> S3 level (oversold reversal zone per source);
    ``exit_divisor``=12.0 -> R1 level (first target per source).
    """
    df = _prep(price_df)
    close = df["close"].astype(float)

    exit_level, entry_level, s4 = _camarilla_levels(df, entry_divisor, exit_divisor)

    entry = (close < entry_level) & (close > s4)
    exit_signal = close > exit_level

    entry = entry.fillna(False)
    exit_signal = exit_signal.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
    close = df["close"].astype(float)
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
