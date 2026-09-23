"""Strategy: MACD + Stochastic synchronized "Double Cross" dual-confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-024):
Per The Forex Geek's "MACD Stochastic Double Cross Strategy"
(https://theforexgeek.com/macd-stochastic-double-cross-strategy/): a long
entry requires BOTH the MACD line crossing above its own signal line
(trend/momentum direction) AND the Stochastic %K line crossing above %D
(momentum-exhaustion/reversal confirmation), with both crossovers occurring
within a short synchronization window. This is distinct from this repo's
Schaff Trend Cycle (STC) family (6+ prior entries) -- STC internally fuses
MACD and a double-stochastic smoothing into ONE composite oscillator via a
specific recursive formula, whereas this strategy keeps MACD and Stochastic
as two SEPARATE raw indicator lines and requires their crossovers to align
in time, following the same synchronized-dual-confirmation pattern already
validated this cron trigger for PPO+TRIX (id 2026-09-24-023).

Signal logic
------------
- MACD_line[t] = EMA(fast_span, close) - EMA(slow_span, close);
  MACD_signal = EMA(macd_signal_span, MACD_line).
- Stochastic %K = SMA(k_smooth) of raw %K (close position within
  stoch_period high/low range); %D = SMA(d_smooth) of %K.
- Entry (long): MACD_line crosses above MACD_signal AND %K crosses above %D,
  with the two cross events occurring within sync_window bars of each
  other (either order).
- Exit: EITHER MACD_line crosses below MACD_signal OR %K crosses below %D,
  OR a max_hold_days time-stop.

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


def _macd(close: pd.Series, fast_span: int, slow_span: int, signal_span: int):
    ema_fast = close.ewm(span=fast_span, adjust=False).mean()
    ema_slow = close.ewm(span=slow_span, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=signal_span, adjust=False).mean()
    return macd_line, macd_signal


def _stochastic(df: pd.DataFrame, stoch_period: int, k_smooth: int, d_smooth: int):
    low_min = df["low"].rolling(stoch_period).min()
    high_max = df["high"].rolling(stoch_period).max()
    raw_k = 100.0 * (df["close"] - low_min) / (high_max - low_min).replace(0, pd.NA)
    raw_k = raw_k.fillna(50.0)
    k = raw_k.rolling(k_smooth).mean()
    d = k.rolling(d_smooth).mean()
    return k, d


def generate_signals(
    price_df: pd.DataFrame,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal_span: int = 9,
    stoch_period: int = 14,
    k_smooth: int = 3,
    d_smooth: int = 3,
    sync_window: int = 2,
    max_hold_days: int = 40,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a {0,leverage_cap} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    macd_line, macd_sig = _macd(close, macd_fast, macd_slow, macd_signal_span)
    k, d = _stochastic(df, stoch_period, k_smooth, d_smooth)

    macd_above = macd_line > macd_sig
    macd_cross_up = macd_above & (~macd_above.shift(1).fillna(False))
    macd_below = macd_line < macd_sig
    macd_cross_down = macd_below & (~macd_below.shift(1).fillna(True))

    k_above = k > d
    k_cross_up = k_above & (~k_above.shift(1).fillna(False))
    k_below = k < d
    k_cross_down = k_below & (~k_below.shift(1).fillna(True))

    macd_cross_up_roll = macd_cross_up.rolling(2 * sync_window + 1, center=True, min_periods=1).max().astype(bool)
    k_cross_up_roll = k_cross_up.rolling(2 * sync_window + 1, center=True, min_periods=1).max().astype(bool)
    entry = (macd_cross_up & k_cross_up_roll) | (k_cross_up & macd_cross_up_roll)

    exit_signal = macd_cross_down | k_cross_down

    position = pd.Series(0.0, index=close.index, dtype=float)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0.0
                continue
            position.iloc[i] = leverage_cap
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = leverage_cap
            else:
                position.iloc[i] = 0.0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
