"""Strategy: Coppock Curve "trough-turn" signal (buy when the curve turns
upward from a local trough while still below the zero line), distinct from
the standard zero-line-cross rule.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-099):
Per a Google AI-overview synthesis of Coppock Curve strategy guides
(LightningChart, TradingView explainers), besides the standard "buy on
zero-line cross" rule, "some traders buy when the indicator line simply
turns upward from a trough while still below zero, though zero-crossings
remain the safest baseline rule" -- i.e. an earlier, more aggressive entry
trigger than waiting for the full zero-cross. This repo already tested the
standard zero-cross version (2026-09-04-036: accepted QQQ only, SPY
near-miss, crypto rejected, at DAILY frequency using the source's original
monthly (11,14)-period ROC counts as a deliberate frequency-mismatch stress
test). This iteration tests the ALTERNATIVE trough-turn trigger instead,
keeping the same daily-frequency-with-monthly-ROC-periods setup for direct
comparability, to see if entering earlier (at the trough, before zero is
crossed) improves or degrades results versus the already-tested zero-cross
version.

Signal logic
------------
- Coppock Curve = WMA(wma_window) of (ROC(close, roc_long) + ROC(close, roc_short)).
- Entry (long): curve makes a local trough (curve[t-1] < curve[t-2] i.e.
  was falling, and curve[t] > curve[t-1] i.e. now turning up) AND
  curve[t] < 0 (still below zero -- the "early" aggressive entry).
- Exit: curve turns back down (curve[t] < curve[t-1] while curve was still
  rising, i.e. a fresh local peak) OR curve crosses above the
  exit_zero_level (locks in gains once momentum confirms positive), OR a
  max_hold_days time-stop.
- Flat otherwise.

Interface contract: both generate_signals and generate_returns accept all
tunable parameters as keyword arguments (grid_test.py calls
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


def _wma(series: pd.Series, window: int) -> pd.Series:
    weights = pd.Series(range(1, window + 1), dtype=float)
    return series.rolling(window).apply(
        lambda x: (x * weights.values).sum() / weights.sum(), raw=True
    )


def _coppock(close: pd.Series, roc_long: int, roc_short: int, wma_window: int) -> pd.Series:
    roc_l = close.pct_change(roc_long) * 100
    roc_s = close.pct_change(roc_short) * 100
    return _wma(roc_l + roc_s, wma_window)


def generate_signals(
    price_df: pd.DataFrame,
    roc_long: int = 14,
    roc_short: int = 11,
    wma_window: int = 10,
    exit_zero_level: float = 0.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    curve = _coppock(close, roc_long, roc_short, wma_window)

    was_falling = curve.shift(1) < curve.shift(2)
    now_rising = curve > curve.shift(1)
    trough_turn = was_falling & now_rising & (curve < 0)

    was_rising = curve.shift(1) > curve.shift(2)
    now_falling = curve < curve.shift(1)
    peak_turn = was_rising & now_falling

    exit_zero_cross = curve > exit_zero_level

    entry = trough_turn.fillna(False)
    exit_signal = (peak_turn | exit_zero_cross).fillna(False)

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
