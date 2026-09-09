"""Strategy: Aroon dual-threshold strong-uptrend confirmation (Aroon-Up>70
AND Aroon-Down<30 simultaneously), long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-082):
Per multiple converging sources (Pocket Option, LiteFinance, surfaced via
Google search snippet -- "The strong uptrend signal appears when the level
of Aroon Up is above 70 and the level of Aroon Down is below 30"), a
simultaneous dual-threshold confirmation (both lines independently signal
strength/weakness at the same time) should be a more robust uptrend
confirmation than either single-line threshold in isolation. Distinct from
the existing repo Aroon variants: Aroon-Down-ONLY absolute threshold
(2026-09-04-031, accepted QQQ) and Aroon Oscillator DIFFERENCE zero-cross
(2026-09-04-063, near-miss SPY) -- neither requires both raw lines to
independently clear their own threshold simultaneously.

Signal logic
------------
- Aroon-Up(period) = 100 * (period - bars_since_period_high) / period.
- Aroon-Down(period) = 100 * (period - bars_since_period_low) / period.
- Entry (long): Aroon-Up crosses from <=up_threshold to >up_threshold WHILE
  Aroon-Down is already < down_threshold (fresh strong-uptrend confirmation).
- Exit: Aroon-Up drops back below up_threshold, OR Aroon-Down rises back
  above down_threshold, OR a max_hold_days time-stop.
- Flat otherwise; long-only, no shorting (per SAFETY.md).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly across a parameter grid).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _aroon(df: pd.DataFrame, period: int) -> tuple[pd.Series, pd.Series]:
    high, low = df["high"], df["low"]

    def bars_since_high(window: pd.Series) -> float:
        return float(len(window) - 1 - window.values.argmax())

    def bars_since_low(window: pd.Series) -> float:
        return float(len(window) - 1 - window.values.argmin())

    bars_since_period_high = high.rolling(period + 1).apply(bars_since_high, raw=False)
    bars_since_period_low = low.rolling(period + 1).apply(bars_since_low, raw=False)

    aroon_up = 100.0 * (period - bars_since_period_high) / period
    aroon_down = 100.0 * (period - bars_since_period_low) / period
    return aroon_up, aroon_down


def generate_signals(
    price_df: pd.DataFrame,
    aroon_period: int = 25,
    up_threshold: float = 70.0,
    down_threshold: float = 30.0,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    aroon_up, aroon_down = _aroon(df, aroon_period)

    prev_up = aroon_up.shift(1)
    fresh_up_cross = (aroon_up > up_threshold) & (prev_up <= up_threshold)
    down_confirmed = aroon_down < down_threshold

    entry = fresh_up_cross & down_confirmed.fillna(False)
    exit_up_weak = aroon_up < up_threshold
    exit_down_strong = aroon_down > down_threshold

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_up_weak.iloc[i]) or bool(exit_down_strong.iloc[i]) or held >= max_hold_days:
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
