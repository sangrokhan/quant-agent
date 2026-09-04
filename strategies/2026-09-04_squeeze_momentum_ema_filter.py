"""Strategy: LazyBear Squeeze Momentum Indicator (SMI) breakout, gated by
a 50-day EMA trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-126):
LazyBear's Squeeze Momentum Indicator (built on John Carter's TTM Squeeze
concept) detects volatility squeezes when Bollinger Bands(20,2std) sit
fully inside Keltner Channels(20-EMA +/- kc_mult*ATR(20)); a squeeze
"release"/"fire" occurs when BB expands back outside KC. A linear-regression
momentum histogram (close minus the average of the rolling
highest-high/lowest-low midpoint and SMA, run through linear regression)
gauges direction/acceleration. Per enlightenedstocktrading.com's own
systematic-trading rule example: "Enter long on the first green dot [squeeze
release with rising momentum] after a squeeze if the histogram is rising and
price is above the 50-day EMA." This is distinct from the already-rejected
plain TTM Squeeze test (2026-09-04-091, no trend filter, momentum proxy used
a Donchian/EMA average) by adding the source's explicit EMA-50 trend filter
and using the first-signal-only (not continuous) entry rule.

Signal logic
------------
- BB: SMA(bb_window) +/- bb_std*STD(bb_window).
- KC: EMA(kc_window) +/- kc_mult*ATR(kc_window).
- squeeze_on = BB fully inside KC (upper_bb < upper_kc and lower_bb > lower_kc).
- Momentum histogram: linear-regression slope-based proxy = close minus
  average of (rolling max(high)+min(low))/2 and SMA(close), over mom_window,
  then linearly detrended (approximated via a simple rolling linear
  regression value) -- momentum is "rising" when today's value > yesterday's.
- squeeze_fired = squeeze_on was True yesterday and is False today (first
  release bar).
- Entry (long): squeeze_fired AND momentum > 0 AND momentum rising AND
  close > EMA(trend_window=50).
- Exit: momentum turns negative, OR close crosses back below EMA(trend_window),
  OR max_hold_days elapses.
- Long-only, flat otherwise.

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


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(period).mean()


def _linreg_value(series: pd.Series, window: int) -> pd.Series:
    x = np.arange(window)
    x_mean = x.mean()
    denom = ((x - x_mean) ** 2).sum()

    def _fit_last(y: np.ndarray) -> float:
        y_mean = y.mean()
        slope = ((x - x_mean) * (y - y_mean)).sum() / denom
        intercept = y_mean - slope * x_mean
        return slope * (window - 1) + intercept  # predicted value at the last point

    return series.rolling(window).apply(_fit_last, raw=True)


def generate_signals(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    kc_window: int = 20,
    kc_mult: float = 1.5,
    mom_window: int = 20,
    trend_window: int = 50,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close, high, low = df["close"], df["high"], df["low"]

    sma = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()
    upper_bb = sma + bb_std * std
    lower_bb = sma - bb_std * std

    ema_kc = close.ewm(span=kc_window, adjust=False).mean()
    atr = _atr(df, kc_window)
    upper_kc = ema_kc + kc_mult * atr
    lower_kc = ema_kc - kc_mult * atr

    squeeze_on = (upper_bb < upper_kc) & (lower_bb > lower_kc)
    squeeze_fired = (squeeze_on.shift(1).fillna(False)) & (~squeeze_on.fillna(False))

    highest_high = high.rolling(mom_window).max()
    lowest_low = low.rolling(mom_window).min()
    donchian_mid = (highest_high + lowest_low) / 2.0
    sma_close = close.rolling(mom_window).mean()
    raw_mom_input = close - (donchian_mid + sma_close) / 2.0
    momentum = _linreg_value(raw_mom_input, mom_window)
    momentum_rising = momentum > momentum.shift(1)

    trend_ema = close.ewm(span=trend_window, adjust=False).mean()
    above_trend = close > trend_ema

    entry_trigger = (
        squeeze_fired.fillna(False)
        & (momentum > 0).fillna(False)
        & momentum_rising.fillna(False)
        & above_trend.fillna(False)
    )

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            mom_i = momentum.iloc[i]
            below_trend_i = not bool(above_trend.iloc[i]) if pd.notna(above_trend.iloc[i]) else False
            neg_mom = bool(mom_i < 0) if pd.notna(mom_i) else False
            if neg_mom or below_trend_i or hold_count >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
                in_pos = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    kc_window: int = 20,
    kc_mult: float = 1.5,
    mom_window: int = 20,
    trend_window: int = 50,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        df,
        bb_window=bb_window,
        bb_std=bb_std,
        kc_window=kc_window,
        kc_mult=kc_mult,
        mom_window=mom_window,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
