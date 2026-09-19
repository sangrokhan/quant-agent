"""Strategy: Down-Day Streak Reversal (continuous streak-length trigger) with
200-day trend filter + inverse-vol sizing -- rescue of 2026-09-20-065 near-miss.

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD):
Direct follow-up to this cron trigger's own recorded near-miss
(2026-09-20-065, N-Day Pullback Reversal): SPY passed 4/5 validators
cleanly at pullback_days=3/hold_days=5 (Sharpe 1.006, MDD 6.2%, TC-survival
0.738, walk-forward 1.0) but failed parameter sensitivity (rel_std 0.656)
because the hard N-day cutoff created a cliff -- pullback_days=4 collapsed
Sharpe to near-zero/negative while 2-3 clustered around 0.85-1.01. This
iteration's own suggested follow-up (recorded in that entry's notes) was
to try "a smoother pullback-day analog (e.g. weighted count instead of
hard N-day cutoff) to reduce the parameter-cliff."

Same source (Quantpedia's "Testing an AI-Assisted Research Workflow for
Multi-Asset Pullback Strategy Discovery"), same trend filter (SMA 200) and
fixed-hold + inverse-vol sizing mechanics, but the pullback TRIGGER is
now the actual LENGTH of the current down-day streak (computed
continuously every bar, not just checked against one hard N), entering as
soon as the streak reaches `min_streak` and staying eligible for entry
while the streak is anywhere in [`min_streak`, `max_streak`] (a band
rather than a single cutoff) -- this smooths the cliff-edge sensitivity
the parent found at N=4 by allowing a RANGE of qualifying streak lengths
rather than one exact count.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _down_streak_length(close: pd.Series) -> pd.Series:
    """Length of the current consecutive-down-day streak as of each bar
    (0 if today closed up or flat)."""
    is_down = (close.diff() < 0).astype(int)
    streak = pd.Series(0, index=close.index, dtype=int)
    current = 0
    for i in range(len(close)):
        if is_down.iloc[i] == 1:
            current += 1
        else:
            current = 0
        streak.iloc[i] = current
    return streak


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    min_streak: int = 2,
    max_streak: int = 5,
    hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(trend_window).mean()
    trend_filter = close > sma

    streak = _down_streak_length(close)
    band_ok = (streak >= min_streak) & (streak <= max_streak)

    entry_trigger = (band_ok & trend_filter).shift(1).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    countdown = 0
    for i in range(len(close)):
        if countdown > 0:
            position.iloc[i] = 1
            countdown -= 1
        elif bool(entry_trigger.iloc[i]):
            position.iloc[i] = 1
            countdown = hold_days - 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    min_streak: int = 2,
    max_streak: int = 5,
    hold_days: int = 5,
    vol_window: int = 20,
    target_vol: float = 0.15,
    max_leverage: float = 1.0,
) -> pd.Series:
    """Position-weighted daily returns with inverse-vol sizing."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df, trend_window=trend_window, min_streak=min_streak,
        max_streak=max_streak, hold_days=hold_days,
    )

    daily_ret = close.pct_change()
    realized_vol = daily_ret.rolling(vol_window).std() * math.sqrt(252)
    exposure = (target_vol / realized_vol).clip(upper=max_leverage).fillna(0.0)

    strategy_ret = position.shift(1).fillna(0) * exposure.shift(1).fillna(0) * daily_ret.fillna(0.0)
    return strategy_ret
