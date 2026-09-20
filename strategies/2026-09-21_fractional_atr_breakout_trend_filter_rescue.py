"""Strategy: Fractional-ATR-Distance Breakout with Trend Filter + ATR Stop.

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD):
Second rescue attempt for the fractional-ATR-distance breakout family
(originally 2026-09-20-137, rejected on max-drawdown with no stop-loss;
then 2026-09-21-188 this same cron trigger added an ATR stop-loss which
improved but did not fully fix the drawdown -- explicitly flagged in that
entry's notes: "the next fix should add a regime filter ... rather than a
purely per-trade risk control"). This iteration keeps the ATR stop-loss
AND adds a trend filter (only take breakout entries when close > SMA(
trend_window), i.e. skip the signal entirely during established
downtrends) on the theory that most of the strategy's drawdown comes from
repeatedly buying ATR-distance breakouts during choppy/declining markets
where the "breakout" is really just noise, not a valid momentum signal.

Signal logic
------------
- Same entry trigger as before: today's high clears prior close +
  atr_frac * ATR(atr_window).
- NEW: entry only fires if close[t-1] > SMA(trend_window) (skip if not in
  an established uptrend).
- Same ATR-multiple stop-loss (stop_atr_mult) and fixed-bar exit
  (hold_days) as the prior 2026-09-21-188 rescue.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    atr_window: int = 10,
    atr_frac: float = 0.25,
    hold_days: int = 5,
    stop_atr_mult: float = 2.0,
    trend_window: int = 100,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    atr = _atr(df, atr_window)
    entry_level = close.shift(1) + atr_frac * atr.shift(1)
    sma_trend = close.rolling(trend_window).mean()
    uptrend = close.shift(1) > sma_trend.shift(1)
    entry_trigger = ((high >= entry_level) & uptrend).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_level = 0.0

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if low.iloc[i] <= stop_level:
                in_position = False
                position.iloc[i] = 0
                continue
            if held >= hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
                in_position = True
                entry_idx = i
                entry_price = entry_level.iloc[i]
                atr_at_entry = atr.shift(1).iloc[i]
                if pd.isna(atr_at_entry):
                    atr_at_entry = 0.0
                stop_level = entry_price - stop_atr_mult * atr_at_entry
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
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
