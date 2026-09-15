"""Strategy: HalfTrend (everget, 2021) ATR-based trend-following.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
HalfTrend (Alex Orekhov "everget", published 2021, GPL-3.0, full Pine v6
source disclosed at https://www.tradingview.com/script/U1SJ8ubc-HalfTrend/)
is an ATR-based trend-following indicator similar to SuperTrend but with a
different trend-identification mechanism: it tracks a running max-low-price
(in a candidate downtrend-to-uptrend transition) / min-high-price (mirror),
and flips its internal trend state when an `amplitude`-period SMA of
high/low crosses the tracked extreme AND the close breaks the prior bar's
low/high. The HalfTrend line itself then tracks either a rising "up" level
(uptrend) or falling "down" level (downtrend), each anchored at trend-flip
time to the *other* level's most recent value (a hysteresis mechanic
distinct from a simple ATR-multiple trailing stop like SuperTrend/
Chandelier Exit, both already tested in this repo). An ATR(100)/2-scaled
deviation channel is plotted around the HalfTrend line but not used for
entries in the source's own disclosed rule -- only the trend-state flip
(buySignal/sellSignal in the source) drives entries/exits. First HalfTrend
strategy in this repo -- distinct construction from SuperTrend, Chandelier
Exit, and Optimized Trend Tracker (other ATR/trailing-stop trend-followers
already tested) via its unique running-extreme-plus-SMA-cross state
machine.

Signal logic
------------
- Long (position=1) whenever the internal trend state is 0 (uptrend, per
  the source's own convention -- trend flips from 1 (down) to 0 (up) on a
  buySignal event).
- Flat (position=0) whenever trend state is 1 (downtrend); long-only per
  this repo's contract (no short entries).
- Optional max_hold_days safety cap.

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


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    tr = _true_range(high, low, close)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def _halftrend_state(
    high: pd.Series, low: pd.Series, close: pd.Series, amplitude: int, channel_deviation: float
) -> pd.Series:
    """Returns a 0/1 trend-state series (0=uptrend, 1=downtrend), per the
    exact recursive state machine in everget's disclosed Pine source.
    """
    n = len(close)
    atr2 = (_atr(high, low, close, 100) / 2.0).to_numpy()

    high_price = high.rolling(amplitude + 1, min_periods=1).max().to_numpy()
    low_price = low.rolling(amplitude + 1, min_periods=1).min().to_numpy()
    high_ma = high.rolling(amplitude, min_periods=1).mean().to_numpy()
    low_ma = low.rolling(amplitude, min_periods=1).mean().to_numpy()

    h = high.to_numpy()
    l = low.to_numpy()
    c = close.to_numpy()

    trend = np.zeros(n, dtype=int)
    next_trend = np.zeros(n, dtype=int)
    max_low_price = np.zeros(n)
    min_high_price = np.zeros(n)
    up = np.full(n, np.nan)
    down = np.full(n, np.nan)

    max_low_price[0] = l[0]
    min_high_price[0] = h[0]

    for i in range(n):
        prev_low = l[i - 1] if i > 0 else l[i]
        prev_high = h[i - 1] if i > 0 else h[i]
        if i == 0:
            trend[i] = 0
            next_trend[i] = 0
            up[i] = max_low_price[i]
            continue

        trend[i] = trend[i - 1]
        next_trend[i] = next_trend[i - 1]
        max_low_price[i] = max_low_price[i - 1]
        min_high_price[i] = min_high_price[i - 1]

        if next_trend[i] == 1:
            max_low_price[i] = max(low_price[i], max_low_price[i])
            if high_ma[i] < max_low_price[i] and c[i] < prev_low:
                trend[i] = 1
                next_trend[i] = 0
                min_high_price[i] = high_price[i]
        else:
            min_high_price[i] = min(high_price[i], min_high_price[i])
            if low_ma[i] > min_high_price[i] and c[i] > prev_high:
                trend[i] = 0
                next_trend[i] = 1
                max_low_price[i] = low_price[i]

        if trend[i] == 0:
            if trend[i - 1] != 0:
                up[i] = down[i - 1] if not np.isnan(down[i - 1]) else np.nan
            else:
                prev_up = up[i - 1] if not np.isnan(up[i - 1]) else max_low_price[i]
                up[i] = max(max_low_price[i], prev_up)
        else:
            if trend[i - 1] != 1:
                down[i] = up[i - 1] if not np.isnan(up[i - 1]) else np.nan
            else:
                prev_down = down[i - 1] if not np.isnan(down[i - 1]) else min_high_price[i]
                down[i] = min(min_high_price[i], prev_down)

    return pd.Series(trend, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    amplitude: int = 2,
    channel_deviation: float = 2.0,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series (long when HalfTrend state=uptrend)."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]
    trend_state = _halftrend_state(high, low, close, amplitude, channel_deviation)
    position = (trend_state == 0).astype(int)

    if max_hold_days and max_hold_days > 0:
        pos = position.values.copy()
        hold = 0
        for i in range(len(pos)):
            if pos[i] == 1:
                hold += 1
                if hold > max_hold_days:
                    pos[i] = 0
                    hold = 0
            else:
                hold = 0
        position = pd.Series(pos, index=position.index)

    return position.reindex(df.index).fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    amplitude: int = 2,
    channel_deviation: float = 2.0,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        df, amplitude=amplitude, channel_deviation=channel_deviation, max_hold_days=max_hold_days
    )
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)
    return position.shift(1).fillna(0) * daily_ret
