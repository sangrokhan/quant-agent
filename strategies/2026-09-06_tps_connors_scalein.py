"""Strategy: Larry Connors' TPS (Trend/Pullback/Signal, aka Time/Price
Scale-in) strategy with position-size scaling.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-185):
Larry Connors' TPS strategy combines a long-term trend filter with a
short-term 2-period RSI oversold pullback signal, then SCALES IN the
position size over several days if price continues pulling back against
the initial entry -- rather than committing full size on the first signal.
Per QuantifiedStrategies.com / the Scribd-hosted rule summary:
  1. Trend filter: close > 200-day EMA (only trade long in an uptrend).
  2. Entry trigger: 2-period RSI < rsi_entry_threshold (25) for 2
     consecutive days -> on the 2nd day's close, take an initial 10% of
     full position size.
  3. Scale-in: on each of the next up-to-3 days, IF that day's close is
     lower than the previous entry day's close, add to the position:
     +20% (day 3), +30% (day 4), +40% (day 5) of full size (cumulative
     10/30/60/100%). If a scale-in day's close is NOT lower than the prior
     entry, that day's scale-in tranche is skipped (position stays at its
     current weight) -- position never exceeds 100% and the schedule does
     not repeat/restart once the 3-day scale-in window has passed.
  4. Exit: when 2-period RSI closes above rsi_exit_threshold (70), exit
     the ENTIRE position (regardless of scale-in level) at that day's
     close.
This is the first non-binary (fractional position weight in [0,1], not a
simple 0/1 flag) strategy in this repo -- distinct from the already-
accepted single-shot binary Connors RSI(2) strategy (id=2026-09-03-005),
which tests whether the position wide-averaging (dollar-cost-averaging into
weakness before the trend confirms) improves risk-adjusted returns over a
single full-size entry.

Interface note: generate_signals here returns a fractional weight Series in
[0, 1] rather than a strict {0,1} flag (the TPS strategy's core mechanic IS
partial position sizing) -- generate_returns still returns a plain daily
return Series compatible with the grid tester / validators.
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
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def generate_signals(
    price_df: pd.DataFrame,
    trend_ema_window: int = 200,
    rsi_window: int = 2,
    rsi_entry_threshold: float = 25.0,
    rsi_exit_threshold: float = 70.0,
    scale_in_weights: tuple = (0.10, 0.20, 0.30, 0.40),
    max_scale_in_days: int = 3,
) -> pd.Series:
    """Return a fractional [0,1] position-weight series."""
    df = _prep(price_df)
    close = df["close"]

    trend_ema = close.ewm(span=trend_ema_window, adjust=False).mean()
    uptrend = close > trend_ema

    rsi = _rsi(close, rsi_window)
    oversold_2day = (rsi < rsi_entry_threshold) & (rsi.shift(1) < rsi_entry_threshold)
    entry_trigger = (oversold_2day & uptrend).fillna(False)
    exit_trigger = (rsi > rsi_exit_threshold).fillna(False)

    weight = pd.Series(0.0, index=close.index, dtype=float)
    in_position = False
    current_weight = 0.0
    last_entry_price = None
    scale_ins_done = 0

    for i in range(len(close)):
        px = close.iloc[i]
        if in_position:
            if bool(exit_trigger.iloc[i]):
                in_position = False
                current_weight = 0.0
                last_entry_price = None
                scale_ins_done = 0
                weight.iloc[i] = 0.0
                continue
            if scale_ins_done < max_scale_in_days and (last_entry_price is not None) and px < last_entry_price:
                current_weight = min(1.0, current_weight + scale_in_weights[scale_ins_done + 1])
                last_entry_price = px
                scale_ins_done += 1
            weight.iloc[i] = current_weight
        else:
            if bool(entry_trigger.iloc[i]):
                in_position = True
                current_weight = scale_in_weights[0]
                last_entry_price = px
                scale_ins_done = 0
                weight.iloc[i] = current_weight
            else:
                weight.iloc[i] = 0.0
    return weight


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    weight = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = weight.shift(1).fillna(0) * daily_ret
    return strategy_ret
