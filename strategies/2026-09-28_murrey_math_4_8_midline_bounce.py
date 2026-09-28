"""Strategy: Murrey Math 4/8 midline support-bounce, long-only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-28-084):
Rescue attempt for the prior near-miss 2026-09-16-180 (Murrey Math octave
support bounce off the 0/8 "ultimate support" line, rejected: best cell
Sharpe 0.992 just under the 1.0 threshold, pass_fraction 0/216). Per
onetradingmarkets.com/otmacademy's Murrey Math Lines guide (read this
iteration via browser_exec, https://www.onetradingmarkets.com/otmacademy/
academy/murrey-math-lines-support-resistance-guide), the source's own
emphasis is that 0/8 is the rarest/hardest level to reach ("ultimate"
support, tested infrequently), whereas the 4/8 line is explicitly called
"the strongest support/resistance INSIDE the Murrey frame" and "one of the
best price areas to look for fresh long or short setups" -- i.e. a much
more frequently-tested, higher-quality level than 0/8. This iteration swaps
the entry trigger from 0/8-touch-and-reclaim to 4/8-touch-and-reclaim
(price dips to/through the midline octave and recloses above it), keeping
everything else (rolling-octave construction, 4/8 take-profit target
replaced by 6/8, ATR-based overshoot stop, time-stop) structurally
identical to 2026-09-16-180 so this isolates the "which octave line" choice
as the fix, per the source's own stated ranking of level quality.

Murrey Math octave construction: over a rolling lookback_n-bar window,
0/8 = rolling min(low), 8/8 = rolling max(high), increment = (8/8-0/8)/8,
so the n/8 line = 0/8 + n*increment. Long entry: bar's low touches/breaches
the 4/8 line (close(t-1) was above 4/8, low(t) <= 4/8) AND close(t)
reclaims back above 4/8 (support-hold confirmation). Exit: close crosses
above the 6/8 line (take-profit, the next major stall/reversal pivot above
4/8 per source), OR close drops below 4/8 - overshoot_buffer_mult*increment
(stop-loss, support has failed), OR max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series {0,1}
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


def _murrey_octaves(df: pd.DataFrame, lookback_n: int) -> tuple[pd.Series, pd.Series]:
    """Return (line_4_8, increment) rolling series."""
    roll_low = df["low"].rolling(lookback_n).min()
    roll_high = df["high"].rolling(lookback_n).max()
    increment = (roll_high - roll_low) / 8.0
    line_4_8 = roll_low + 4 * increment
    return line_4_8, increment


def generate_signals(
    price_df: pd.DataFrame,
    lookback_n: int = 32,
    overshoot_buffer_mult: float = 0.25,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    low = df["low"]

    line_4_8, increment = _murrey_octaves(df, lookback_n)
    line_6_8 = line_4_8 + 2 * increment
    stop_line = line_4_8 - overshoot_buffer_mult * increment

    prev_close_above = close.shift(1) > line_4_8
    touched = low <= line_4_8
    reclaimed = close > line_4_8
    entry = touched & reclaimed & prev_close_above.fillna(False)

    exit_tp = close > line_6_8
    exit_sl = close < stop_line

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if pd.isna(line_4_8.iloc[i]):
            position.iloc[i] = 0
            continue
        if in_position:
            held = i - entry_idx
            if bool(exit_tp.iloc[i]) or bool(exit_sl.iloc[i]) or held >= max_hold_days:
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
