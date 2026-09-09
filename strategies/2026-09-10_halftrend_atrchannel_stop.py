"""Strategy: HalfTrend flip + ATR channel trailing-stop exit (SPY near-miss fix).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-014):
Direct follow-up to accepted 2026-09-10-013 (plain HalfTrend trend-flip,
QQQ all-validators-pass, SPY near-miss Sharpe 0.996 vs 1.0 threshold across
its entire local parameter sweep). everget's original HalfTrend source
(https://www.tradingview.com/script/U1SJ8ubc-HalfTrend, verified via GitHub
pradip-interra/PineScripts strategy_ht_ce_pd_rsi_combined.ps) ALSO computes
`atrHigh`/`atrLow` channel bands (the HalfTrend line +/- channel_deviation
* ATR(atr_window)/2) that the plain trend-flip strategy left completely
unused -- it only used the discrete trend-state flip for entry/exit. This
variant adds an explicit early-exit rule: exit the long position as soon as
close crosses below the `atrLow` band (source's own drawn lower channel
boundary), in addition to the existing mirror-flip and max_hold_days exits,
to see if tighter, source-native risk control rescues SPY's narrow Sharpe
shortfall without needing an external stop-loss mechanism.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _halftrend_state(df: pd.DataFrame, amplitude: int = 2, channel_deviation: float = 2.0, atr_window: int = 100):
    """Reimplements everget's HalfTrend state machine (trend: 0=up, 1=down)
    plus the source's own ATR-based atrHigh/atrLow channel bands."""
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    n = len(df)

    highma = df["high"].rolling(amplitude).mean().values
    lowma = df["low"].rolling(amplitude).mean().values
    high_price = df["high"].rolling(amplitude).max().values
    low_price = df["low"].rolling(amplitude).min().values

    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - df["close"].shift()).abs()
    tr3 = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / atr_window, adjust=False).mean().values
    atr2 = atr / 2.0
    dev = channel_deviation * atr2

    trend = np.zeros(n, dtype=int)
    next_trend = np.zeros(n, dtype=int)
    max_low_price = np.full(n, np.nan)
    min_high_price = np.full(n, np.nan)
    up = np.full(n, np.nan)
    down = np.full(n, np.nan)
    atr_low = np.full(n, np.nan)

    max_low_price[0] = low[0]
    min_high_price[0] = high[0]

    for i in range(1, n):
        prev_next_trend = next_trend[i - 1]
        prev_max_low = max_low_price[i - 1] if not np.isnan(max_low_price[i - 1]) else low[i - 1]
        prev_min_high = min_high_price[i - 1] if not np.isnan(min_high_price[i - 1]) else high[i - 1]

        trend[i] = trend[i - 1]
        next_trend[i] = prev_next_trend
        max_low_price[i] = prev_max_low
        min_high_price[i] = prev_min_high

        if not (np.isnan(highma[i]) or np.isnan(lowma[i]) or np.isnan(high_price[i]) or np.isnan(low_price[i])):
            if prev_next_trend == 1:
                max_low_price[i] = max(low_price[i], prev_max_low)
                if highma[i] < max_low_price[i] and close[i] < low[i - 1]:
                    trend[i] = 1
                    next_trend[i] = 0
                    min_high_price[i] = high_price[i]
            else:
                min_high_price[i] = min(high_price[i], prev_min_high)
                if lowma[i] > min_high_price[i] and close[i] > high[i - 1]:
                    trend[i] = 0
                    next_trend[i] = 1
                    max_low_price[i] = low_price[i]

        if trend[i] == 0:
            if trend[i - 1] != 0:
                up[i] = down[i - 1] if not np.isnan(down[i - 1]) else (up[i - 1] if not np.isnan(up[i - 1]) else max_low_price[i])
            else:
                prev_up = up[i - 1] if not np.isnan(up[i - 1]) else max_low_price[i]
                up[i] = max(max_low_price[i], prev_up)
            atr_low[i] = up[i] - dev[i]
        else:
            if trend[i - 1] != 1:
                down[i] = up[i - 1] if not np.isnan(up[i - 1]) else (down[i - 1] if not np.isnan(down[i - 1]) else min_high_price[i])
            else:
                prev_down = down[i - 1] if not np.isnan(down[i - 1]) else min_high_price[i]
                down[i] = min(min_high_price[i], prev_down)
            atr_low[i] = down[i] - dev[i]

    return trend, atr_low


def generate_signals(
    price_df: pd.DataFrame,
    amplitude: int = 2,
    channel_deviation: float = 2.0,
    atr_window: int = 100,
    max_hold_days: int = 60,
) -> pd.Series:
    df = _prep(price_df)
    trend, atr_low = _halftrend_state(df, amplitude, channel_deviation, atr_window)
    trend_s = pd.Series(trend, index=df.index)
    atr_low_s = pd.Series(atr_low, index=df.index)
    close = df["close"]

    buy_signal = (trend_s == 0) & (trend_s.shift(1) == 1)
    sell_signal = (trend_s == 1) & (trend_s.shift(1) == 0)
    channel_stop_hit = close < atr_low_s

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    entry_idx = -1
    idx_list = df.index.tolist()

    for i in range(1, len(df)):
        ts = idx_list[i]
        if not in_pos:
            if bool(buy_signal.iloc[i]):
                in_pos = True
                entry_idx = i
        else:
            days_held = i - entry_idx
            stop_hit = bool(channel_stop_hit.iloc[i]) if not np.isnan(atr_low_s.iloc[i]) else False
            if bool(sell_signal.iloc[i]) or stop_hit or days_held >= max_hold_days:
                in_pos = False
            else:
                position.loc[ts] = 1

        if in_pos and i >= entry_idx:
            position.loc[ts] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(price_df, **params)
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    return strat_returns
