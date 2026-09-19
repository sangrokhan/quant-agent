"""Strategy: Bear Power Zero-Cross Entry with Chandelier Trailing Stop Exit
-- BUGFIX rescue of 2026-09-20-070 (degenerate 1-trade signal).

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD):
Direct rescue of this cron trigger's own rejected entry 2026-09-20-070
(Bear Power entry + Chandelier trailing stop exit, per Kryptera's "The
Regime Report" Medium article). That entry's post-mortem in this cron
trigger's own investigation (not a new external source) found the
rejection was NOT due to a weak signal but a genuine IMPLEMENTATION BUG:
the exit-loop's `running_stop` ratchet variable could get initialized to
NaN on an early entry (before the Chandelier ATR/highest-high rolling
windows had enough history to produce a valid value), and because NaN
comparisons in Python are always False, `running_stop` then silently
NEVER updated again for the rest of that entire trade -- meaning the
"trailing stop" exit condition (`price < running_stop`) could never fire
once running_stop was NaN, effectively locking the position open forever
after the very first entry. This explains why the parent's grid showed
exactly 1 trade regardless of any exit parameter (chandelier_window,
atr_mult) tested -- the exit mechanism was silently disabled by the bug,
not by the entry being too rare.

This entry fixes the bug (always adopt the first valid/non-NaN Chandelier
stop value even if `running_stop` is momentarily NaN, and never let a NaN
running_stop block the ratchet-update check) with the exact same
signal/exit design as the parent, to test whether the underlying Bear
Power + Chandelier idea has real edge once the exit mechanism actually
functions.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    ema_window: int = 13,
    chandelier_window: int = 22,
    atr_mult: float = 3.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    ema = close.ewm(span=ema_window, adjust=False).mean()
    bear_power = low - ema
    ema_rising = ema > ema.shift(1)

    bear_power_rising = bear_power > bear_power.shift(1)
    bear_power_negative = bear_power < 0
    entry_trigger = (bear_power_rising & bear_power_negative & ema_rising).shift(1).fillna(False)

    atr = _atr(df, chandelier_window)
    highest_high = high.rolling(chandelier_window).max()
    chandelier_long_stop = highest_high - atr_mult * atr

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    running_stop = None
    for i in range(len(close)):
        px = close.iloc[i]
        cs = chandelier_long_stop.iloc[i]
        cs_valid = cs == cs  # NaN check (NaN != NaN)
        if in_position:
            # BUGFIX vs parent: never let a NaN running_stop persist --
            # always adopt the first valid cs even if running_stop is
            # currently None/NaN, and only compare cs>running_stop when
            # running_stop itself is a valid number.
            if cs_valid and (running_stop is None or running_stop != running_stop or cs > running_stop):
                running_stop = cs
            if running_stop is not None and running_stop == running_stop and px < running_stop:
                in_position = False
                running_stop = None
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
                in_position = True
                running_stop = cs if cs_valid else None
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
