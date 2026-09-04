"""Strategy: QS RSI (QuantifiedStrategies composite range-position oscillator).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-164):
QuantifiedStrategies.com's own "QS RSI" composite indicator -- averaging (1)
a fast 3-day RSI, (2) the close's position within the current day's own
high-low range (IBS-style, (close-low)/(high-low)*100), and (3) the close's
position within its trailing 5-day high-low range -- captures both
short-term momentum AND short-term range-location in one 0-100 reading.
A low QS RSI reading (weak momentum + closing near recent range lows)
signals oversold worth a long entry (mean-reversion), gated by a 200-day
SMA uptrend filter (buying dips in an established uptrend, following this
repo's broadly successful RSI2/IBS/Connors-RSI pattern); exit when QS RSI
recovers above an exit threshold or after a max_hold_days time-stop. Per
QuantifiedStrategies.com's QS RSI Strategy article (78% win rate, 214
trades on QQQ -- exact numeric entry/exit thresholds paywalled, formula
itself fully disclosed). Distinct from Connors RSI (2026-09-04-113, uses
streak-length + ROC percentrank components) since QS RSI's second and third
components are pure range-POSITION measures (IBS-like), not
streak-length/percentrank.

Signal logic
------------
- RSI3 = RSI(close, window=3) via Wilder smoothing.
- Day-range position = (close - low) / (high - low) * 100 (IBS scaled to
  0-100, single-day).
- 5-day-range position = (close - rolling_5d_low) / (rolling_5d_high -
  rolling_5d_low) * 100.
- QS_RSI = mean(RSI3, day_range_position, five_day_range_position).
- Trend filter: close > SMA(trend_window).
- Entry (long): QS_RSI crosses below entry_threshold AND close > SMA(trend_window).
- Exit: QS_RSI crosses above exit_threshold, OR trend filter breaks (close
  < SMA(trend_window)), OR max_hold_days elapses.
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and
grid_test.py: generate_signals/generate_returns take price_df plus keyword
params.
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


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _qs_rsi(df: pd.DataFrame, rsi_window: int, range_window: int) -> pd.Series:
    close, high, low = df["close"], df["high"], df["low"]

    rsi3 = _rsi(close, rsi_window)

    day_range = (high - low).replace(0.0, np.nan)
    day_pos = ((close - low) / day_range * 100.0).fillna(50.0)

    roll_low = low.rolling(range_window).min()
    roll_high = high.rolling(range_window).max()
    roll_range = (roll_high - roll_low).replace(0.0, np.nan)
    range5_pos = ((close - roll_low) / roll_range * 100.0).fillna(50.0)

    qs_rsi = (rsi3 + day_pos + range5_pos) / 3.0
    return qs_rsi


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 3,
    range_window: int = 5,
    entry_threshold: float = 20.0,
    exit_threshold: float = 70.0,
    trend_window: int = 200,
    max_hold_days: int = 10,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    qs_rsi = _qs_rsi(df, rsi_window, range_window)
    trend_sma = close.rolling(trend_window).mean()

    cross_below_entry = (qs_rsi < entry_threshold) & (qs_rsi.shift(1) >= entry_threshold)
    cross_above_exit = (qs_rsi > exit_threshold) & (qs_rsi.shift(1) <= exit_threshold)
    uptrend = close > trend_sma
    trend_break = (close < trend_sma) & (close.shift(1) >= trend_sma.shift(1))

    entry_raw = cross_below_entry & uptrend
    exit_raw = cross_above_exit | trend_break

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_days = 0
    entry_arr = entry_raw.fillna(False).to_numpy()
    exit_arr = exit_raw.fillna(False).to_numpy()
    pos_arr = position.to_numpy().copy()

    for i in range(len(df)):
        if in_pos:
            hold_days += 1
            if exit_arr[i] or hold_days >= max_hold_days:
                in_pos = False
                hold_days = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if entry_arr[i]:
                in_pos = True
                hold_days = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    position = pd.Series(pos_arr, index=df.index, dtype=int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    rsi_window: int = 3,
    range_window: int = 5,
    entry_threshold: float = 20.0,
    exit_threshold: float = 70.0,
    trend_window: int = 200,
    max_hold_days: int = 10,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        rsi_window=rsi_window,
        range_window=range_window,
        entry_threshold=entry_threshold,
        exit_threshold=exit_threshold,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
