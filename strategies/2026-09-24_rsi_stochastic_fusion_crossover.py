"""Strategy: RSI + Stochastic "Fusion Crossover" dual-confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-026):
Per "RSI and Stochastic Indicator Fusion Crossover Strategy" (Medium,
Sword Red, https://medium.com/@redsword_23261/rsi-and-stochastic-indicator-
fusion-crossover-strategy-3546f7bb39a1): the source's disclosed buy signal
combines (a) RSI rising AND below a buy threshold (default 37), (b)
Stochastic %K below an oversold line (default 20) WITH a golden cross (%K
crosses above %D), and (c) RSI crossing above its own smoothed-RSI line.
This implementation keeps legs (a) and (b) -- RSI-rising-below-threshold
AND Stochastic-golden-cross-in-oversold-zone, synchronized within a short
window -- and drops leg (c) (RSI vs. its own smoothed line) as a scope
reduction for tractability within one iteration; noted explicitly so a
future iteration can add the third leg back as a refinement. This is
distinct from this repo's prior separate RSI and Stochastic entries (never
combined into a synchronized dual-confirmation gate) and from this cron
trigger's PPO+TRIX (2026-09-24-023) and MACD+Stochastic (2026-09-24-024)
dual-confirmation pairs (different indicator pairing: RSI threshold-rising
condition, not a signal-line crossover, paired with Stochastic's golden
cross specifically inside the oversold zone).

Signal logic
------------
- RSI(rsi_period) on close (Wilder's recursive smoothing).
- Stochastic %K = SMA(k_smooth) of raw %K; %D = SMA(d_smooth) of %K.
- RSI condition: RSI[t] > RSI[t-1] (rising) AND RSI[t] < rsi_buy_threshold.
- Stochastic condition: %K crosses above %D (golden cross) while %K is
  below stoch_oversold at the cross bar.
- Entry (long): both conditions true within sync_window bars of each other.
- Exit: RSI falls AND rises above rsi_sell_threshold (source's mirrored
  bearish condition, long-only adapted to a flat exit), OR Stochastic
  death cross (%K crosses below %D) while %K is above stoch_overbought,
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


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


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
    rsi_period: int = 14,
    rsi_buy_threshold: float = 37.0,
    rsi_sell_threshold: float = 63.0,
    stoch_period: int = 14,
    k_smooth: int = 3,
    d_smooth: int = 3,
    stoch_oversold: float = 20.0,
    stoch_overbought: float = 80.0,
    sync_window: int = 2,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rsi = _rsi(close, rsi_period)
    k, d = _stochastic(df, stoch_period, k_smooth, d_smooth)

    rsi_rising_below = (rsi > rsi.shift(1)) & (rsi < rsi_buy_threshold)

    k_above = k > d
    golden_cross = k_above & (~k_above.shift(1).fillna(False)) & (k < stoch_oversold)
    k_below = k < d
    death_cross = k_below & (~k_below.shift(1).fillna(True)) & (k > stoch_overbought)

    rsi_rising_below_roll = rsi_rising_below.rolling(2 * sync_window + 1, center=True, min_periods=1).max().astype(bool)
    golden_cross_roll = golden_cross.rolling(2 * sync_window + 1, center=True, min_periods=1).max().astype(bool)
    entry = (rsi_rising_below & golden_cross_roll) | (golden_cross & rsi_rising_below_roll)

    rsi_falling_above = (rsi < rsi.shift(1)) & (rsi > rsi_sell_threshold)
    exit_signal = rsi_falling_above | death_cross

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
