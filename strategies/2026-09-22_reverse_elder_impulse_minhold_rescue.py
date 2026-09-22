"""Strategy: Reverse Elder Impulse System, min-hold-days rescue.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-072):
Direct rescue attempt for this same cron trigger's own rejection
2026-09-22-071 (Reverse Elder Impulse, Neutral->Negative transition trigger,
decisive Sharpe+TC-survival near-miss fail on both QQQ (Sharpe 0.803, TC
0.443) and SPY (Sharpe 0.974, TC 0.498) -- ~290 trades over 7.75yr eroded a
modest but real edge via transaction costs; walk-forward/MDD/param-sensitivity
all already passed, so the fix target is specifically trade FREQUENCY, not
directional logic). Adds a min_hold_days gate (once in a position, ignore
exit signals -- i.e. ignore the Neutral-state exit trigger -- until N days
have elapsed), the established repo pattern from
strategies/2026-09-04_kvo_crossover_minhold.py, on top of the unchanged
Neutral->Negative entry trigger and underlying EMA/MACD-Histogram impulse
classification. The 2026-09-22-071 grid already showed an SMA trend-gate
rescue makes average Sharpe WORSE on every equity cell (0.292 base config,
worse gated) -- this is a genuinely different rescue lever targeting the
actual bottleneck (trade count) rather than re-trying the failed gate
pattern from other rescues this cron trigger.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _macd_histogram(close: pd.Series, fast: int, slow: int, signal: int) -> pd.Series:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line - signal_line


def generate_signals(
    price_df: pd.DataFrame,
    ema_window: int = 13,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    trend_window: int = 0,
    min_hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ema = close.ewm(span=ema_window, adjust=False).mean()
    hist = _macd_histogram(close, macd_fast, macd_slow, macd_signal)

    ema_rising = ema > ema.shift(1)
    hist_rising = hist > hist.shift(1)
    ema_falling = ema < ema.shift(1)
    hist_falling = hist < hist.shift(1)

    green = ema_rising & hist_rising  # bullish impulse
    red = ema_falling & hist_falling  # bearish impulse
    state = pd.Series(0, index=df.index, dtype=int)
    state[green] = 1
    state[red] = -1

    prev_state = state.shift(1).fillna(0)

    if trend_window and trend_window > 0:
        sma = close.rolling(trend_window).mean()
        uptrend = close > sma
    else:
        uptrend = pd.Series(True, index=df.index)

    entry_trigger = (prev_state == 0) & (state == -1) & uptrend

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    days_held = 0
    for i in range(len(df)):
        if in_position:
            days_held += 1
            if state.iloc[i] == 0 and days_held >= min_hold_days:
                in_position = False
                days_held = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
                in_position = True
                days_held = 0
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
