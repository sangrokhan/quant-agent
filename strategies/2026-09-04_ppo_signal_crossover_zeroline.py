"""Strategy: Percentage Price Oscillator (PPO) signal-line crossover, gated
by the PPO zero-line trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-109):
Per quantifiedstrategies.com's PPO article (percentage-price-oscillator/),
the PPO (100 * (EMA_fast - EMA_slow) / EMA_slow) crossing above its own
9-period EMA signal line marks a positive short-term momentum shift, and
is confirmed as a genuine trend (not noise) when PPO is also above zero
(i.e. fast EMA > slow EMA, a medium-term uptrend). This is a MACD-family
zero-line + signal-line combo not yet tried in this repo (prior entries
used raw MACD histogram inflection (2026-09-04-100) or MACD+Elder/Schaff/
Triple-Screen combos, but never PPO's normalized percentage-difference
version with the specific signal-cross+zero-line-confirm entry rule).

Signal logic
------------
- ppo = 100 * (EMA(fast) - EMA(slow)) / EMA(slow)
- signal = EMA(signal_window) of ppo
- Entry (long): ppo crosses above signal (bullish momentum shift) AND
  ppo > 0 at that bar (zero-line trend confirmation, per the source's own
  "these short-term shifts... are confirmed when the indicator crosses the
  zero level" framing).
- Exit: ppo crosses back below signal, OR ppo drops below zero (trend
  filter breaks), OR after max_hold_days (avoid indefinite holds).
- Flat otherwise.

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


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 12,
    slow_window: int = 26,
    signal_window: int = 9,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ema_fast = close.ewm(span=fast_window, adjust=False).mean()
    ema_slow = close.ewm(span=slow_window, adjust=False).mean()
    ppo = 100.0 * (ema_fast - ema_slow) / ema_slow
    signal = ppo.ewm(span=signal_window, adjust=False).mean()

    bullish_cross = (ppo > signal) & (ppo.shift(1) <= signal.shift(1))
    bearish_cross = (ppo < signal) & (ppo.shift(1) >= signal.shift(1))
    above_zero = ppo > 0

    entry = bullish_cross & above_zero.fillna(False)
    exit_cross = bearish_cross
    exit_trend = ~above_zero.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or bool(exit_trend.iloc[i]) or held >= max_hold_days:
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
