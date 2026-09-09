"""Strategy: HalfTrend indicator (everget's TradingView construction) trend flip.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-013):
Per everget's HalfTrend indicator
(https://www.tradingview.com/script/U1SJ8ubc-HalfTrend), sourced via GitHub
(pradip-interra/PineScripts strategy_ht_ce_pd_rsi_combined.ps, which
faithfully re-implements everget's original v4 script in v5): HalfTrend is
a state-machine trailing trend line distinct from Supertrend/Chandelier
Exit -- it tracks the max of a rolling `amplitude`-bar lowest-low (while in
an uptrend state) or the min of a rolling `amplitude`-bar highest-high
(while in a downtrend state), and flips its internal "next trend" state
using a comparison between SMA(high, amplitude)/SMA(low, amplitude) and
those running extremes, confirmed by a raw close vs. yesterday's high/low
crossing. The published trading rule (buySignal/sellSignal in the source)
is: go long when the state flips from trend==1 (down) to trend==0 (up);
go flat/exit on the mirror flip.

This is a genuinely distinct construction from every trailing-stop-flip
strategy already in this repo (SuperTrend id=2026-09-04-053, Chandelier
Exit id=2026-09-09-064, Parabolic SAR id=2026-09-04-042, Gann HiLo
Activator id=2026-09-05-017) because of its two-stage "candidate next
trend, confirm on next close-vs-prior-bar-extreme" state machine (a flip
requires BOTH the SMA-vs-running-extreme condition AND a raw close
breaking the prior bar's high/low, not a single ATR-band crossing like
SuperTrend/Chandelier, nor a pure stop-and-reverse like Parabolic SAR).

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


def _halftrend_state(df: pd.DataFrame, amplitude: int = 2):
    """Reimplements everget's HalfTrend state machine (trend: 0=up, 1=down)."""
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    n = len(df)

    highma = df["high"].rolling(amplitude).mean().values
    lowma = df["low"].rolling(amplitude).mean().values
    high_price = df["high"].rolling(amplitude).max().values  # highest high over amplitude bars
    low_price = df["low"].rolling(amplitude).min().values    # lowest low over amplitude bars

    trend = np.zeros(n, dtype=int)
    next_trend = np.zeros(n, dtype=int)
    max_low_price = np.full(n, np.nan)
    min_high_price = np.full(n, np.nan)

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

        if np.isnan(highma[i]) or np.isnan(lowma[i]) or np.isnan(high_price[i]) or np.isnan(low_price[i]):
            continue

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

    return trend


def generate_signals(
    price_df: pd.DataFrame,
    amplitude: int = 2,
    max_hold_days: int = 60,
) -> pd.Series:
    df = _prep(price_df)
    trend = _halftrend_state(df, amplitude)
    trend_s = pd.Series(trend, index=df.index)

    # per source: buySignal when trend flips from 1(down) -> 0(up)
    buy_signal = (trend_s == 0) & (trend_s.shift(1) == 1)
    sell_signal = (trend_s == 1) & (trend_s.shift(1) == 0)

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
            if bool(sell_signal.iloc[i]) or days_held >= max_hold_days:
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
