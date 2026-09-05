"""Strategy: Connors RSI (CRSI) with volume-exhaustion confirmation filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-042):
Builds on the plain Connors RSI mean-reversion strategy already accepted for
QQQ in this repo (id=2026-09-04-113): long when close > 200d SMA (structural
uptrend) AND CRSI closes below entry_threshold (oversold). Per Google's
AI-overview synthesis (citing TuringTrader, Papers With Backtest, Aron
Groups Broker, Traders Mastermind, LuxAlgo) of the "Connors Volume-Weighted
Price Reversal Strategy", the key addition beyond plain CRSI is a **volume
exhaustion confirmation**: the oversold trigger bar's volume should be BELOW
its own recent average volume, evidencing that the sell-off is running out
of participation/conviction (a low-volume capitulation drift, not a
high-volume institutional distribution event) -- this is meant to filter
out oversold signals accompanied by heavy continued selling (which the
source frames as more likely to keep falling) from oversold signals on
thinning volume (more likely to be a genuine exhaustion bottom). Exit when
CRSI closes back above exit_threshold (mid-scale/recovery), or a
max_hold_days time-stop backstop. First strategy in this repo combining
CRSI with an explicit volume-based entry filter -- distinct from the plain
CRSI baseline (2026-09-04-113) which has no volume condition at all.

Signal logic
------------
- CRSI(rsi_period, streak_period, pctrank_period) computed identically to
  the already-accepted 2026-09-04_connors_rsi_composite_meanrev.py.
- Volume exhaustion: today's volume < vol_ma_window-day average volume *
  vol_exhaustion_ratio (default 1.0 = below its own recent average).
- Entry (long): close > 200d SMA (trend filter) AND CRSI < entry_threshold
  AND volume exhaustion condition holds.
- Exit: CRSI > exit_threshold, OR max_hold_days time-stop.
- Flat otherwise (long-only; no short leg per SAFETY.md scope).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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


def _wilder_rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    return rsi


def _updown_streak(close: pd.Series) -> pd.Series:
    delta = close.diff()
    direction = np.sign(delta).fillna(0.0)
    streak = np.zeros(len(close))
    for i in range(1, len(close)):
        d = direction.iloc[i]
        if d == 0:
            streak[i] = 0.0
        elif d > 0:
            streak[i] = streak[i - 1] + 1 if streak[i - 1] >= 0 else 1
        else:
            streak[i] = streak[i - 1] - 1 if streak[i - 1] <= 0 else -1
    return pd.Series(streak, index=close.index)


def _percent_rank(series: pd.Series, period: int) -> pd.Series:
    def _rank(window: np.ndarray) -> float:
        last = window[-1]
        return 100.0 * (np.sum(window[:-1] <= last) / (len(window) - 1)) if len(window) > 1 else 50.0

    return series.rolling(period + 1).apply(_rank, raw=True)


def _connors_rsi(close: pd.Series, rsi_period: int, streak_period: int, pctrank_period: int) -> pd.Series:
    rsi_price = _wilder_rsi(close, rsi_period)
    streak = _updown_streak(close)
    rsi_streak = _wilder_rsi(streak, streak_period)
    roc1 = close.pct_change(1) * 100.0
    pct_rank = _percent_rank(roc1, pctrank_period)
    return (rsi_price + rsi_streak + pct_rank) / 3.0


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 3,
    streak_period: int = 2,
    pctrank_period: int = 100,
    entry_threshold: float = 15.0,
    exit_threshold: float = 70.0,
    trend_window: int = 200,
    vol_ma_window: int = 20,
    vol_exhaustion_ratio: float = 1.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    crsi = _connors_rsi(close, rsi_period, streak_period, pctrank_period)
    trend_sma = close.rolling(trend_window).mean()
    vol_avg = volume.rolling(vol_ma_window).mean()

    trend_ok = close > trend_sma
    vol_exhaustion = volume < (vol_avg * vol_exhaustion_ratio)

    valid = crsi.notna() & trend_sma.notna() & vol_avg.notna()

    entry = (crsi < entry_threshold) & trend_ok & vol_exhaustion & valid
    exit_signal = (crsi > exit_threshold) & valid

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(len(df)):
        if not valid.iloc[i]:
            position.iloc[i] = 1 if in_pos else 0
            continue
        if in_pos:
            hold_count += 1
            if exit_signal.iloc[i] or hold_count >= max_hold_days:
                in_pos = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if entry.iloc[i]:
                in_pos = True
                hold_count = 0
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
