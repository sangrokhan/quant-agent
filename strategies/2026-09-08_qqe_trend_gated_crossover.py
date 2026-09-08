"""Strategy: QQE (Quantitative Qualitative Estimation) fast/slow trailing-band
crossover, trend-filtered.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
The QQE indicator (Wilders/Ehlers-lineage smoothed-RSI construction) builds
two ATR-of-RSI trailing "ratchet" bands (fast and slow) around a smoothed
RSI line. Per howtotrade.com's QQE trading-strategy tutorial
(https://howtotrade.com/indicators/qqe-indicator/), a bullish setup occurs
when: (1) all three lines (smoothed RSI, fast trailing band, slow trailing
band) sit below the 50-level (regime confirmation -- avoids buying into an
already-overbought market), and (2) the smoothed-RSI line crosses above the
slow trailing band (momentum-shift trigger). The source recommends
confirming with a longer-term trend filter (e.g. price above a 100-period
EMA) to only take longs aligned with the broader trend, which we implement
here as a `trend_ema_window`-period EMA gate. Exit on the opposite
crossover (smoothed RSI back below the slow trailing band), OR the
smoothed RSI regime flipping to >=50 without a confirmed cross (safety
exit), OR a `max_hold_days` time-stop.

This is distinct from the repo's existing RVI-family and Stochastic-family
entries: QQE's trailing bands are an ATR-of-RSI-delta ratchet (similar
mechanically to a Supertrend/Chandelier construction, but applied to a
smoothed RSI oscillator rather than to price/ATR directly), not a simple
signal-line SMA crossover. First QQE entry in this repo.

Interface contract for validators (see validation/validators.py) /
grid_test.py (see validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _wilder_ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(alpha=1.0 / period, adjust=False).mean()


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = _wilder_ema(up, period)
    roll_down = _wilder_ema(down, period).replace(0, np.nan)
    rs = roll_up / roll_down
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _qqe_trailing_line(rsi_ma: pd.Series, wilders_period: int, factor: float) -> pd.Series:
    """Compute one QQE ATR-of-RSI trailing ratchet band around rsi_ma."""
    atr_rsi = rsi_ma.diff().abs()
    ma_atr_rsi = _wilder_ema(atr_rsi, wilders_period)
    dar = _wilder_ema(ma_atr_rsi, wilders_period) * factor

    upperband = rsi_ma + dar
    lowerband = rsi_ma - dar

    n = len(rsi_ma)
    trail = np.empty(n)
    trail[:] = np.nan
    if n == 0:
        return pd.Series(trail, index=rsi_ma.index)

    trail[0] = lowerband.iloc[0] if not np.isnan(lowerband.iloc[0]) else 50.0
    rsi_vals = rsi_ma.values
    lb_vals = lowerband.values
    ub_vals = upperband.values

    for i in range(1, n):
        prev_trail = trail[i - 1]
        if np.isnan(prev_trail):
            prev_trail = lb_vals[i]
        cur_rsi = rsi_vals[i]
        prev_rsi = rsi_vals[i - 1]
        if np.isnan(cur_rsi) or np.isnan(lb_vals[i]) or np.isnan(ub_vals[i]):
            trail[i] = prev_trail
            continue
        if cur_rsi > prev_trail and prev_rsi > prev_trail:
            trail[i] = max(prev_trail, lb_vals[i])
        elif cur_rsi < prev_trail and prev_rsi < prev_trail:
            trail[i] = min(prev_trail, ub_vals[i])
        elif cur_rsi > prev_trail:
            trail[i] = lb_vals[i]
        else:
            trail[i] = ub_vals[i]
    return pd.Series(trail, index=rsi_ma.index)


def _compute_qqe(
    df: pd.DataFrame,
    rsi_period: int,
    smooth_period: int,
    wilders_period: int,
    fast_factor: float,
    slow_factor: float,
):
    rsi = _rsi(df["close"], rsi_period)
    rsi_ma = rsi.ewm(span=smooth_period, adjust=False).mean()
    fast_line = _qqe_trailing_line(rsi_ma, wilders_period, fast_factor)
    slow_line = _qqe_trailing_line(rsi_ma, wilders_period, slow_factor)
    return rsi_ma, fast_line, slow_line


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 14,
    smooth_period: int = 5,
    wilders_period: int = 14,
    fast_factor: float = 1.618,
    slow_factor: float = 4.236,
    trend_ema_window: int = 100,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    rsi_ma, fast_line, slow_line = _compute_qqe(
        df, rsi_period, smooth_period, wilders_period, fast_factor, slow_factor
    )

    trend_ema = close.ewm(span=trend_ema_window, adjust=False).mean()
    trend_ok = close > trend_ema

    below_50_all = (rsi_ma < 50) & (fast_line < 50) & (slow_line < 50)
    bullish_cross = (rsi_ma > slow_line) & (rsi_ma.shift(1) <= slow_line.shift(1))
    entry = below_50_all & bullish_cross & trend_ok

    bearish_cross = (rsi_ma < slow_line) & (rsi_ma.shift(1) >= slow_line.shift(1))
    regime_flip = rsi_ma >= 50

    n = len(df)
    position = np.zeros(n, dtype=int)
    entry_vals = entry.fillna(False).values
    exit_signal_vals = (bearish_cross | regime_flip).fillna(False).values

    in_pos = False
    hold_days = 0
    for i in range(n):
        if in_pos:
            hold_days += 1
            if exit_signal_vals[i] or hold_days >= max_hold_days:
                in_pos = False
                hold_days = 0
            else:
                position[i] = 1
        if not in_pos and entry_vals[i]:
            in_pos = True
            hold_days = 0
            position[i] = 1

    return pd.Series(position, index=df.index, name="position")


def generate_returns(
    price_df: pd.DataFrame,
    rsi_period: int = 14,
    smooth_period: int = 5,
    wilders_period: int = 14,
    fast_factor: float = 1.618,
    slow_factor: float = 4.236,
    trend_ema_window: int = 100,
    max_hold_days: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        df,
        rsi_period=rsi_period,
        smooth_period=smooth_period,
        wilders_period=wilders_period,
        fast_factor=fast_factor,
        slow_factor=slow_factor,
        trend_ema_window=trend_ema_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret.rename("returns")
