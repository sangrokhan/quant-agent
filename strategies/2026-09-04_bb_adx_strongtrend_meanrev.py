"""Strategy: Bollinger Band lower-touch mean reversion gated by ADX trend-strength.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-162):
A close falling below the lower Bollinger Band (20-period, 2 std) while
ADX(14) is simultaneously ABOVE a strength threshold (25, confirming a
genuinely strong directional trend rather than noise/chop) marks a
higher-quality mean-reversion long entry than an ungated BB lower-touch,
since the band break is happening during a confirmed strong move (more
likely to snap back / less likely to be random noise). Per StockSharp's
worked "Bollinger Adx Strategy" example (Entry Criteria: Close < LowerBand
&& ADX > AdxThreshold; Exit: Bollinger mean reversion to the middle band;
reports ~46% avg annual backtested return on stocks, though timeframe/robustness
unverified). Exit when price reverts back to the middle band (SMA) or a
max_hold_days time-stop. First BB+ADX combination tested in this repo
(distinct from 2026-09-03-023's BB+ATR-percentile+MA-slope-flatness gate,
which explicitly required LOW volatility/flat trend rather than a STRONG
trend, and from 2026-09-03-017's pure ADX/DMI crossover with no Bollinger
component).

Signal logic
------------
- Bollinger Bands: SMA(bb_window) +/- bb_std * rolling std.
- ADX(adx_window) via Wilder's smoothing of +DM/-DM/TR.
- Entry (long): close crosses below the lower band AND ADX > adx_threshold
  at that bar.
- Exit: close crosses back above the middle band (SMA), OR max_hold_days
  elapses since entry.
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


def _bollinger(close: pd.Series, window: int, num_std: float) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = close.rolling(window).mean()
    std = close.rolling(window).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return upper, mid, lower


def _adx(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    plus_dm_s = pd.Series(plus_dm, index=df.index).ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    minus_dm_s = pd.Series(minus_dm, index=df.index).ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()

    plus_di = 100 * (plus_dm_s / atr.replace(0.0, np.nan))
    minus_di = 100 * (minus_dm_s / atr.replace(0.0, np.nan))
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    adx = dx.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    return adx.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    adx_window: int = 14,
    adx_threshold: float = 25.0,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    upper, mid, lower = _bollinger(close, bb_window, bb_std)
    adx = _adx(df, adx_window)

    cross_below_lower = (close < lower) & (close.shift(1) >= lower.shift(1))
    entry_raw = cross_below_lower & (adx > adx_threshold)
    exit_raw = (close > mid) & (close.shift(1) <= mid.shift(1))

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
    bb_window: int = 20,
    bb_std: float = 2.0,
    adx_window: int = 14,
    adx_threshold: float = 25.0,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        bb_window=bb_window,
        bb_std=bb_std,
        adx_window=adx_window,
        adx_threshold=adx_threshold,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
