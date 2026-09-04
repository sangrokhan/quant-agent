"""Strategy: Inside Bar breakout with EMA trend filter and N-bar breakout expiry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-090):
An "Inside Bar" (IB) is a bar whose high/low range is fully contained within
the prior "Mother Bar" (MB): IB.high <= MB.high AND IB.low >= MB.low. This
signals a consolidation/volatility-contraction pause. Per StrategyQuant/
Secuora/TradingView guides, the concrete mechanical rule is: only take long
breakout signals when price is above a trend filter (50 or 200-period EMA),
enter long when price closes above (or intrabar breaks above, approximated
here with next-bar close since this repo only has daily OHLCV, not
intrabar ticks) the Mother Bar's high within `breakout_expiry_bars` bars of
the inside bar forming (setup expires/cancels otherwise), and exit on a
trend-filter break or after `max_hold_days`.

Signal logic (daily-bar approximation -- no intrabar stop orders available)
------------------------------------------------------------------------
- Detect inside bar at t: high[t] <= high[t-1] AND low[t] >= low[t-1]
  (mother bar = bar t-1).
- If close[t] (or any close within the next `breakout_expiry_bars` bars) >
  mother_bar_high AND close is above `ema_window`-EMA (trend filter): enter
  long on that breakout bar's close.
- If no breakout occurs within `breakout_expiry_bars` bars after the inside
  bar, the setup expires (no entry).
- Exit: close crosses back below the EMA trend filter, OR `max_hold_days`
  elapsed since entry, whichever first.

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


def generate_signals(
    price_df: pd.DataFrame,
    ema_window: int = 50,
    breakout_expiry_bars: int = 2,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    is_inside_bar = (high <= high.shift(1)) & (low >= low.shift(1))
    mother_bar_high = high.shift(1)  # the bar preceding the inside bar

    ema_trend = close.ewm(span=ema_window, adjust=False).mean()
    above_trend = close > ema_trend

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    pending_setup_bar = -1  # index of the inside-bar formation
    pending_mb_high = np.nan

    for i in range(n):
        if in_pos:
            hold_count += 1
            exit_trigger = (not bool(above_trend.iloc[i])) or hold_count >= max_hold_days
            if exit_trigger:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
            continue

        # Not in position: check for a pending breakout setup expiry, or a new inside bar.
        if pending_setup_bar >= 0:
            bars_since_setup = i - pending_setup_bar
            if bars_since_setup > breakout_expiry_bars:
                pending_setup_bar = -1  # setup expired
            else:
                breakout = close.iloc[i] > pending_mb_high
                if breakout and bool(above_trend.iloc[i]):
                    in_pos = True
                    hold_count = 0
                    position.iloc[i] = 1
                    pending_setup_bar = -1
                    continue

        if bool(is_inside_bar.iloc[i]) and not np.isnan(mother_bar_high.iloc[i]):
            pending_setup_bar = i
            pending_mb_high = mother_bar_high.iloc[i]

        position.iloc[i] = 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    ema_window: int = 50,
    breakout_expiry_bars: int = 2,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        ema_window=ema_window,
        breakout_expiry_bars=breakout_expiry_bars,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
