"""Strategy: Pivot Point SuperTrend (LonesomeTheBlue, TradingView) distance
as a CONTINUOUS SIZING dial within an SMA(trend_window) uptrend gate,
leverage-cap-aware for crypto.

Hypothesis (this cron trigger, iteration 6):
First Pivot Point SuperTrend strategy in this repo. Per the original Pine
Script source (https://github.com/fmzquant/strategies/blob/master/Pivot-Point-Supertrend.md,
LonesomeTheBlue, read this iteration): unlike classic SuperTrend/Chandelier
Exit/HalfTrend/Trend Magic (all already tested in this repo, all anchored
directly to raw price/hl2), Pivot Point SuperTrend anchors its ATR bands to
a weighted-average CENTER LINE built from confirmed swing pivot highs/lows
(center := (center*2 + lastpivot)/3 on each new confirmed pivot), giving the
trailing-stop mechanism a smoother, less noise-reactive anchor than price
itself. Up = center - Factor*ATR(Pd); Dn = center + Factor*ATR(Pd); the
band ratchets in the trend direction exactly like classic SuperTrend, and
the discrete signal is Trend flipping (close crossing the trailing line).

This iteration reframes the discrete trend-flip trigger as a CONTINUOUS
sizing dial, following this repo's established binary-to-continuous-sizing
rescue pattern (successful for SuperTrend/ATR itself, Chandelier, DPO,
Hurst, VHF, TII, RVI, Kalman slope, Ichimoku Kumo-distance, etc.): the
normalized distance between close and the trailing PP-SuperTrend line
(scaled by ATR so it's comparable across regimes) is rolling z-scored and
tanh-squashed into exposure, applied within an SMA(trend_window) uptrend
gate with a deadband. Distinct from every prior SuperTrend-family entry
in this repo since the underlying anchor line uses pivot-point smoothing
rather than raw price.

Source: https://github.com/fmzquant/strategies/blob/master/Pivot-Point-Supertrend.md
(original LonesomeTheBlue Pine Script, read via browser_exec this iteration).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
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


def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
    raw = raw_exposure.fillna(0.0).to_numpy()
    held = np.zeros_like(raw)
    current = 0.0
    for i, r in enumerate(raw):
        if abs(r - current) > deadband:
            current = r
        held[i] = current
    return pd.Series(held, index=raw_exposure.index)


def _pivot_high_low(high: pd.Series, low: pd.Series, prd: int):
    """Confirmed pivot high/low at bar i-prd, confirmed prd bars later
    (needs prd bars on both sides to be the local extreme)."""
    n = len(high)
    ph = np.full(n, np.nan)
    pl = np.full(n, np.nan)
    h = high.to_numpy()
    l = low.to_numpy()
    for i in range(prd, n - prd):
        window_h = h[i - prd:i + prd + 1]
        if h[i] == window_h.max() and np.argmax(window_h) == prd:
            ph[i] = h[i]
        window_l = l[i - prd:i + prd + 1]
        if l[i] == window_l.min() and np.argmin(window_l) == prd:
            pl[i] = l[i]
    return ph, pl


def _pp_center_line(high: pd.Series, low: pd.Series, prd: int) -> pd.Series:
    ph, pl = _pivot_high_low(high, low, prd)
    n = len(high)
    center = np.full(n, np.nan)
    cur = np.nan
    for i in range(n):
        lastpp = ph[i] if not np.isnan(ph[i]) else (pl[i] if not np.isnan(pl[i]) else np.nan)
        if not np.isnan(lastpp):
            cur = lastpp if np.isnan(cur) else (cur * 2 + lastpp) / 3
        center[i] = cur
    return pd.Series(center, index=high.index).ffill()


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr


def _pp_supertrend_line(
    high: pd.Series, low: pd.Series, close: pd.Series,
    pivot_period: int, atr_factor: float, atr_period: int,
) -> pd.Series:
    center = _pp_center_line(high, low, pivot_period)
    tr = _true_range(high, low, close)
    atr = tr.rolling(atr_period).mean()

    up_band = center - atr_factor * atr
    dn_band = center + atr_factor * atr

    n = len(close)
    c = close.to_numpy()
    up = up_band.to_numpy()
    dn = dn_band.to_numpy()
    t_up = np.full(n, np.nan)
    t_down = np.full(n, np.nan)
    trend = np.ones(n)
    trailing = np.full(n, np.nan)

    for i in range(n):
        if i == 0 or np.isnan(t_up[i - 1]):
            t_up[i] = up[i]
        else:
            t_up[i] = max(up[i], t_up[i - 1]) if c[i - 1] > t_up[i - 1] else up[i]
        if i == 0 or np.isnan(t_down[i - 1]):
            t_down[i] = dn[i]
        else:
            t_down[i] = min(dn[i], t_down[i - 1]) if c[i - 1] < t_down[i - 1] else dn[i]

        prev_t_down = t_down[i - 1] if i > 0 else t_down[i]
        prev_t_up = t_up[i - 1] if i > 0 else t_up[i]
        if c[i] > prev_t_down:
            trend[i] = 1
        elif c[i] < prev_t_up:
            trend[i] = -1
        else:
            trend[i] = trend[i - 1] if i > 0 else 1

        trailing[i] = t_up[i] if trend[i] == 1 else t_down[i]

    return pd.Series(trailing, index=close.index), pd.Series(atr, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    pivot_period: int = 5,
    atr_factor: float = 2.0,
    atr_period: int = 10,
    zscore_window: int = 126,
    sensitivity: float = 0.6,
    base_exposure: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    dial = tanh(zscore((close - trailing_line)/atr, zscore_window)) -- close
    further above the trailing PP-SuperTrend line (relative to ATR) pushes
    the dial positive (increase exposure); further below pushes it negative
    (reduce exposure), gated to 0 whenever close is below its
    SMA(trend_window).
    """
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    trend_long = close > close.rolling(trend_window).mean()

    trailing_line, atr = _pp_supertrend_line(high, low, close, pivot_period, atr_factor, atr_period)
    dist = (close - trailing_line) / atr.replace(0.0, np.nan)

    roll_mean = dist.rolling(zscore_window).mean()
    roll_std = dist.rolling(zscore_window).std(ddof=0)
    z = (dist - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(z.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    pivot_period: int = 5,
    atr_factor: float = 2.0,
    atr_period: int = 10,
    zscore_window: int = 126,
    sensitivity: float = 0.6,
    base_exposure: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        pivot_period=pivot_period,
        atr_factor=atr_factor,
        atr_period=atr_period,
        zscore_window=zscore_window,
        sensitivity=sensitivity,
        base_exposure=base_exposure,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
