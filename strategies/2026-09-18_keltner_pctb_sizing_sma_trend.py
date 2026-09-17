"""Strategy: SMA(trend_window) directional gate with continuous Keltner
Channel Oscillator (%B-style) sizing overlay + deadband, leverage-cap aware
for crypto from the start.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-001):
Per https://tradesmart.com/blog/technical-analysis-keltner-channel-oscillator/
(already on file in this repo's ledger from prior entry 2026-09-10-067, not
re-fetched this iteration per dedupe rule -- formula already documented):
Keltner Channel Oscillator = (Price - KC_lower) / (KC_upper - KC_lower) - 0.5,
a %B-style normalized position within an EMA-basis + ATR-width Keltner
Channel, bounded roughly [-0.5, +0.5] under normal conditions (can exceed
those bounds during a breakout). The repo's ONE prior Keltner Oscillator
entry (2026-09-10-067) used it as a BINARY mean-reversion threshold-cross
trigger (long on cross up off -0.5, exit on cross above 0.0) and was
rejected. This iteration applies this cron trigger's own validated
technique (already rescued Bollinger %B, ESD %B, Kirshenbaum, STARC,
Elder AutoEnvelope, Standard Error Bands from discrete-trigger rejections):
reframe the SAME %B-style oscillator as a CONTINUOUS SIZING dial instead of a
discrete entry/exit trigger -- rescale to a zero-centered dial via
osc_centered = clip(oscillator * 2, -1, 1) (oscillator is itself already
roughly [-0.5, 0.5] centered, so *2 maps it near [-1, 1]), used as a sizing
multiplier within an SMA(trend_window) uptrend gate with a deadband to cut
turnover. First Keltner-Channel-Oscillator continuous-sizing variant in this
repo -- distinct from the already-tested plain Keltner Channel breakout
(2026-09-03-016), squeeze constructions (2026-09-04-091/126), mean-reversion
band-touch (2026-09-05-074), and middle-line pullback (2026-09-06-136)
entries, none of which used the normalized %B-style oscillator as a
continuous exposure dial.

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


def _true_range(df: pd.DataFrame) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _keltner_oscillator(
    df: pd.DataFrame, ema_window: int, atr_window: int, atr_mult: float
) -> pd.Series:
    close = df["close"]
    ema = close.ewm(span=ema_window, adjust=False, min_periods=ema_window).mean()
    tr = _true_range(df)
    atr = tr.ewm(span=atr_window, adjust=False, min_periods=atr_window).mean()
    upper = ema + atr_mult * atr
    lower = ema - atr_mult * atr
    band_width = (upper - lower).replace(0.0, np.nan)
    oscillator = (close - lower) / band_width - 0.5
    return oscillator


def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
    raw = raw_exposure.fillna(0.0).to_numpy()
    held = np.zeros_like(raw)
    current = 0.0
    for i, r in enumerate(raw):
        if abs(r - current) > deadband:
            current = r
        held[i] = current
    return pd.Series(held, index=raw_exposure.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    ema_window: int = 20,
    atr_window: int = 20,
    atr_mult: float = 2.0,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    oscillator = _keltner_oscillator(df, ema_window, atr_window, atr_mult)
    osc_centered = (oscillator * 2.0).clip(-1.0, 1.0)

    raw_exposure = base_exposure + sensitivity * osc_centered
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    ema_window: int = 20,
    atr_window: int = 20,
    atr_mult: float = 2.0,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        ema_window=ema_window,
        atr_window=atr_window,
        atr_mult=atr_mult,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
