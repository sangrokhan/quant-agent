"""Strategy: Qstick (Tushar Chande) moving-average-confirmation crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-136):
Per technicalresources.in, the Qstick indicator is an n-period SMA of
(close - open), measuring candle-body-direction momentum (whether recent
bars have tended to close higher or lower than they opened). The source's
"Moving Average Confirmation Strategy" rule: use a second SMA of the
Qstick line itself; buy when Qstick crosses above its own moving average
AND remains positive (both conditions together, stronger confirmation
than a bare zero-line cross); sell/exit when Qstick crosses below its own
moving average and turns negative. This is the first Qstick/candle-body-
momentum strategy tested in this repo (distinct from every prior
candlestick-pattern or OHLC-derived momentum variant, which used raw
patterns or volume-weighted measures, not a smoothed open-close spread).

Signal logic
------------
- qstick = SMA(close - open, qstick_window)
- qstick_ma = SMA(qstick, signal_window)
- Entry (long): qstick crosses above qstick_ma (fresh cross) AND qstick > 0
- Exit: qstick crosses below qstick_ma AND qstick < 0 (mirror condition),
  OR max_hold_days time-stop (source doesn't specify one, added as a
  backstop against indefinite holds).
- Long-only, flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    qstick_window: int = 10,
    signal_window: int = 10,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    n = len(df)

    body = close - open_
    qstick = body.rolling(qstick_window).mean()
    qstick_ma = qstick.rolling(signal_window).mean()

    qstick_prev = qstick.shift(1)
    qstick_ma_prev = qstick_ma.shift(1)

    entry_trigger = (qstick > qstick_ma) & (qstick_prev <= qstick_ma_prev) & (qstick > 0)
    exit_trigger = (qstick < qstick_ma) & (qstick_prev >= qstick_ma_prev) & (qstick < 0)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            et = bool(exit_trigger.iloc[i]) if pd.notna(exit_trigger.iloc[i]) else False
            if et or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            entered = bool(entry_trigger.iloc[i]) if pd.notna(entry_trigger.iloc[i]) else False
            if entered:
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    qstick_window: int = 10,
    signal_window: int = 10,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df, qstick_window=qstick_window, signal_window=signal_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
