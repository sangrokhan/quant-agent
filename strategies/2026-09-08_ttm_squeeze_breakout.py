"""Strategy: TTM Squeeze (John Carter) breakout -- long only.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-003):
Per https://volatilitybox.com/research/ttm-squeeze-indicator/, a volatility
compression state ("squeeze on": 20-period Bollinger Bands, 2 std, contract
fully INSIDE 20-period Keltner Channels, 1.5x ATR) that persists for at
least min_squeeze_len bars, followed by the squeeze releasing ("squeeze
off": Bollinger Bands expand back outside the Keltner Channels), tends to
resolve into a directional breakout -- source claims ~68% directional
accuracy when the momentum histogram aligns, vs ~55-60% for a naive
Bollinger-Bandwidth-only squeeze (no Keltner cross-check). The source's own
momentum histogram (`linreg(close - avg(highest_high, lowest_low,
sma_close), N)`) supplies the direction filter: for the long-only version
required by SAFETY.md, take the breakout only when momentum is positive AND
rising at the moment the squeeze fires, plus the source's own price-action
confirmation (close > 20-SMA). Exit on the source's momentum-deceleration
rule (histogram stops rising while still positive) or a max_hold_days
time-stop. First TTM Squeeze / Bollinger-inside-Keltner strategy in this
repo -- distinct from prior Bollinger Bandwidth squeeze / ATR-expansion
breakout strategies since this specifically requires the dual BB-vs-KC
compression state, not a single-envelope width threshold.

Signal logic
------------
- Bollinger Bands: SMA(bb_window) +/- bb_std * rolling std.
- Keltner Channels: EMA(kc_window) +/- kc_atr_mult * ATR(kc_window) (Wilder ATR).
- squeeze_on = (bb_upper < kc_upper) AND (bb_lower > kc_lower).
- squeeze_off = NOT squeeze_on.
- fire = squeeze_off today AND squeeze_on yesterday AND the squeeze lasted
  >= min_squeeze_len consecutive bars before firing.
- momentum histogram = linear regression (rolling OLS slope*x+intercept,
  evaluated at the last point) of (close - avg(rolling_max(high, N),
  rolling_min(low, N), SMA(close, N))) over a momentum_window lookback.
- Entry (long): fire AND momentum > 0 AND momentum is rising (today's
  momentum > yesterday's) AND close > SMA(bb_window) (price confirmation).
- Exit: momentum stops rising while still positive (decelerating), OR
  momentum crosses to <= 0, OR max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series   ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
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


def _wilder_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def _rolling_linreg_last(series: pd.Series, window: int) -> pd.Series:
    """Rolling OLS slope*x + intercept evaluated at the last point of each window."""
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()

    def _fit_last(y: np.ndarray) -> float:
        y_mean = y.mean()
        slope = ((x - x_mean) * (y - y_mean)).sum() / x_var
        intercept = y_mean - slope * x_mean
        return slope * x[-1] + intercept

    return series.rolling(window, min_periods=window).apply(_fit_last, raw=True)


def _compute_indicators(
    df: pd.DataFrame,
    bb_window: int,
    bb_std: float,
    kc_window: int,
    kc_atr_mult: float,
    momentum_window: int,
):
    close, high, low = df["close"], df["high"], df["low"]

    sma = close.rolling(bb_window, min_periods=bb_window).mean()
    std = close.rolling(bb_window, min_periods=bb_window).std()
    bb_upper = sma + bb_std * std
    bb_lower = sma - bb_std * std

    ema = close.ewm(span=kc_window, adjust=False, min_periods=kc_window).mean()
    atr = _wilder_atr(high, low, close, kc_window)
    kc_upper = ema + kc_atr_mult * atr
    kc_lower = ema - kc_atr_mult * atr

    squeeze_on = (bb_upper < kc_upper) & (bb_lower > kc_lower)

    highest_high = high.rolling(momentum_window, min_periods=momentum_window).max()
    lowest_low = low.rolling(momentum_window, min_periods=momentum_window).min()
    sma_close = close.rolling(momentum_window, min_periods=momentum_window).mean()
    ref = (highest_high + lowest_low + sma_close) / 3.0
    momentum = _rolling_linreg_last(close - ref, momentum_window)

    return sma, squeeze_on, momentum


def generate_signals(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    kc_window: int = 20,
    kc_atr_mult: float = 1.5,
    momentum_window: int = 20,
    min_squeeze_len: int = 6,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    sma, squeeze_on, momentum = _compute_indicators(
        df, bb_window, bb_std, kc_window, kc_atr_mult, momentum_window
    )

    squeeze_on_filled = squeeze_on.fillna(False)
    # consecutive count of squeeze_on bars ending at each index
    grp = (~squeeze_on_filled).cumsum()
    squeeze_run = squeeze_on_filled.groupby(grp).cumsum()
    prev_squeeze_run = squeeze_run.shift(1).fillna(0)

    fire = (~squeeze_on_filled) & squeeze_on_filled.shift(1).fillna(False) & (prev_squeeze_run >= min_squeeze_len)

    momentum_rising = momentum > momentum.shift(1)
    entry = fire & (momentum > 0) & momentum_rising & (close > sma)
    entry = entry.fillna(False)

    n = len(df)
    entry_arr = entry.to_numpy()
    momentum_arr = momentum.to_numpy()
    pos_arr = [0] * n

    in_pos = False
    hold_counter = 0
    for i in range(n):
        if in_pos:
            hold_counter += 1
            mom_now = momentum_arr[i]
            mom_prev = momentum_arr[i - 1] if i > 0 else np.nan
            decelerating = (not np.isnan(mom_now)) and (not np.isnan(mom_prev)) and (mom_now <= mom_prev)
            non_positive = (not np.isnan(mom_now)) and mom_now <= 0
            exit_now = decelerating or non_positive or hold_counter >= max_hold_days
            if exit_now:
                in_pos = False
                hold_counter = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if bool(entry_arr[i]):
                in_pos = True
                hold_counter = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    bb_window: int = 20,
    bb_std: float = 2.0,
    kc_window: int = 20,
    kc_atr_mult: float = 1.5,
    momentum_window: int = 20,
    min_squeeze_len: int = 6,
    max_hold_days: int = 10,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        bb_window=bb_window,
        bb_std=bb_std,
        kc_window=kc_window,
        kc_atr_mult=kc_atr_mult,
        momentum_window=momentum_window,
        min_squeeze_len=min_squeeze_len,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
