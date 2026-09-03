"""Strategy: Elder-Ray (Bull Power / Bear Power) rising-bear-power dip-buy.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-037):
Per Dr. Alexander Elder's Elder-Ray indicator (per Google AI-overview +
TradingView/QuantifiedStrategies snippets, web_search failed with a
DDGS/Yahoo TLS error this iteration, fell back to browser_exec): a
13-period EMA is the baseline "consensus of value"; Bull Power = day's
high - EMA(13) measures buyers' ability to push price above value; Bear
Power = day's low - EMA(13) measures sellers' ability to push price below
value. The long-entry rule requires (1) EMA(13) rising (uptrend filter)
and (2) Bear Power negative but RISING from a lower level (sellers losing
dominance even though price briefly dipped below the EMA -- a bullish
pullback-exhaustion signal within an uptrend). Exit when Bull Power makes a
lower high (buying power fading) or Bear Power turns aggressively more
negative (renewed seller dominance). Long-only per this repo's convention
(source's symmetric short-side rule not implemented).

Signal logic
------------
- EMA(ema_window) baseline; "rising" = EMA(t) > EMA(t - slope_lookback).
- Bull Power = high - EMA; Bear Power = low - EMA.
- Entry (long): EMA rising AND Bear Power < 0 AND Bear Power > Bear Power
  bear_power_lookback bars ago (i.e. rising from a lower level -- momentum
  in the "less negative" direction).
- Exit: Bull Power < its value bull_power_lookback bars ago while EMA was
  still above that same earlier bar's EMA (a genuine lower high in buying
  power, not just daily noise), OR Bear Power drops more than
  bear_power_exit_threshold below its own prior value (a sharp renewed
  seller push).
- Flat otherwise; long-only, no shorting.

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


def generate_signals(
    price_df: pd.DataFrame,
    ema_window: int = 13,
    slope_lookback: int = 3,
    bear_power_lookback: int = 3,
    bull_power_lookback: int = 3,
    bear_power_exit_drop: float = 0.02,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    ema = close.ewm(span=ema_window, adjust=False).mean()
    bull_power = high - ema
    bear_power = low - ema

    ema_rising = ema > ema.shift(slope_lookback)
    bear_power_rising = (bear_power < 0) & (bear_power > bear_power.shift(bear_power_lookback))

    entry = ema_rising.fillna(False) & bear_power_rising.fillna(False)

    bull_power_lower_high = (bull_power < bull_power.shift(bull_power_lookback)) & (
        ema > ema.shift(bull_power_lookback)
    )
    bear_power_sharp_drop = (bear_power - bear_power.shift(1)) < -(bear_power_exit_drop * close)
    exit_signal = bull_power_lower_high.fillna(False) | bear_power_sharp_drop.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
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
