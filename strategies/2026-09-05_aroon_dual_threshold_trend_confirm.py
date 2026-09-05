"""Strategy: Aroon dual-threshold trend confirmation (Aroon Up > 70 AND
Aroon Down < 30), long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-079):
Per AvaTrade's Aroon Indicator Trading Strategies guide: "Aroon Up above 70
and Aroon Down below 30: Strong bullish trend." / "Clear Signal Zones: The
70/30 threshold levels offer straightforward cues for identifying strong
bullish or bearish momentum." This is a dual-threshold BOTH-lines
confirmation rule, distinct from every prior Aroon strategy in this repo:
2026-09-04-031 used only Aroon-Down (a single line: buy when Aroon-Down<20,
sell when Aroon-Down>50, no Aroon-Up condition at all) and 2026-09-04-063
used the Aroon OSCILLATOR (AroonUp-AroonDown difference) crossing zero (a
derived single-line construction). Here both raw Aroon Up and Aroon Down
lines must simultaneously clear their own threshold (>70 and <30
respectively) -- a stricter, dual-condition trend-confirmation entry that
neither prior variant tested.

Signal logic
------------
- AroonUp(t) = 100 * (window - periods_since_highest_high) / window.
- AroonDown(t) = 100 * (window - periods_since_lowest_low) / window.
- Entry (long): AroonUp > up_threshold (70) AND AroonDown < down_threshold
  (30) -- both conditions hold simultaneously (strong bullish trend per
  source).
- Exit: either condition breaks (AroonUp <= up_threshold OR AroonDown >=
  down_threshold), or a max_hold_days time-stop.
- Flat otherwise.

Interface contract (RESEARCH_LOOP.md Step 5):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def _aroon(df: pd.DataFrame, window: int) -> tuple[pd.Series, pd.Series]:
    high = df["high"]
    low = df["low"]

    def periods_since_max(x: np.ndarray) -> float:
        return float(len(x) - 1 - np.argmax(x))

    def periods_since_min(x: np.ndarray) -> float:
        return float(len(x) - 1 - np.argmin(x))

    since_high = high.rolling(window + 1).apply(periods_since_max, raw=True)
    since_low = low.rolling(window + 1).apply(periods_since_min, raw=True)

    aroon_up = 100.0 * (window - since_high) / window
    aroon_down = 100.0 * (window - since_low) / window
    return aroon_up, aroon_down


def generate_signals(
    price_df: pd.DataFrame,
    window: int = 14,
    up_threshold: float = 70.0,
    down_threshold: float = 30.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    aroon_up, aroon_down = _aroon(df, window)

    strong_bull = (aroon_up > up_threshold) & (aroon_down < down_threshold)
    entry = strong_bull.fillna(False)
    exit_cond = ~strong_bull.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    entry_vals = entry.to_numpy()
    exit_vals = exit_cond.to_numpy()

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_vals[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_vals[i]):
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
