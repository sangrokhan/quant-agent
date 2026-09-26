"""Strategy: 3-Day Declining High/Low Pattern + RSI(2)>70 Exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-26-015):
Per a Google AI-overview synthesis of QuantifiedStrategies.com's
"Consecutive Down Days Strategy" content (quantifiedstrategies.substack.com
/consecutive-down-days-strategy, corroborated by their own published
video/social summaries): entry requires (1) close>SMA(200) (structural
bull market trend filter), (2) three consecutive trading days where EACH
day's high AND low are both lower than the prior day's high/low (a
stricter pattern than a simple close-only down-streak -- prior repo
entries 2026-09-08-058/2026-09-20-065/2026-09-22-121 all use close-only or
close-vs-SMA(5) streak definitions, none require the full
declining-high-AND-low bar pattern), (3) buy at the close of the
qualifying (3rd) day. Exit: hold until RSI(2) rises above 70 (source's own
disclosed exit rule, distinct from every other Consecutive-Down-Days
variant in this repo, which use a prior-close cross or SMA(5) cross exit
instead of an RSI(2) threshold).

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


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0.0, 1e-12)
    return 100.0 - (100.0 / (1.0 + rs))


def generate_signals(
    price_df: pd.DataFrame,
    down_streak_days: int = 3,
    rsi_window: int = 2,
    exit_threshold: float = 70.0,
    trend_ma_window: int = 200,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    trend_ok = close > close.rolling(trend_ma_window).mean()

    high_declining = high < high.shift(1)
    low_declining = low < low.shift(1)
    both_declining = high_declining & low_declining
    streak_ok = both_declining.rolling(down_streak_days).sum() == down_streak_days

    entry = streak_ok & trend_ok

    rsi = _rsi(close, rsi_window)
    exit_signal = rsi > exit_threshold

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
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
