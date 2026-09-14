"""Strategy: SMA(trend_window) directional gate with continuous Volume RSI
(VoRSI) sizing overlay + deadband, leverage-cap-aware for crypto from the
start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Volume RSI (VoRSI), per QuantStrategy.io's "How to Trade with Volume RSI
Indicator" article (formula already fully confirmed and reused verbatim
from this repo's existing accepted strategy
strategies/2026-09-09_volume_rsi_50line_crossover.py, no fresh web fetch
needed this sub-step): applies the classic RSI formula to UP/DOWN VOLUME
instead of up/down price changes:
    up_volume[t]   = volume[t] if close[t] > close[t-1] else 0
    down_volume[t] = volume[t] if close[t] < close[t-1] else 0
    avg_up, avg_down = rolling SMA(up_volume, window), SMA(down_volume, window)
    VoRS  = avg_up / avg_down
    VoRSI = 100 - 100/(1+VoRS)     -- naturally bounded [0,100], 50=neutral
This repo's only prior VoRSI entry (2026-09-09-098) used it as a binary
50-line crossover ENTRY trigger (accepted QQQ-only, SPY near-miss, crypto
rejected decisively). This iteration reframes VoRSI as a CONTINUOUS SIZING
dial within an SMA(trend_window) uptrend gate -- the same reframing
pattern that has repeatedly rescued binary-only bounded oscillators
elsewhere in this repo, including two other examples earlier this same
cron trigger (Firefly Oscillator, Elegant Oscillator). Economic rationale:
VoRSI measures which side (buyers vs sellers) is driving the recent
volume -- a persistently high reading (bullish volume dominance) signals
sustained institutional/crowd conviction behind the up-move, warranting
larger exposure within an established uptrend, while VoRSI hovering near
50 signals volume is roughly balanced between up/down days (less
conviction) even while price stays nominally above the SMA trend filter.
First Volume RSI continuous-sizing variant.

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


def _compute_vorsi(close: pd.Series, volume: pd.Series, window: int) -> pd.Series:
    price_change = close.diff()
    up_volume = volume.where(price_change > 0, 0.0)
    down_volume = volume.where(price_change < 0, 0.0)

    avg_up = up_volume.rolling(window).mean()
    avg_down = down_volume.rolling(window).mean()

    safe_down = avg_down.where(avg_down != 0, 1.0)
    vors = avg_up / safe_down
    vorsi = 100 - 100 / (1 + vors)
    vorsi = vorsi.where(avg_down != 0, 100.0)
    vorsi = vorsi.where(~((avg_down == 0) & (avg_up == 0)), 50.0)
    return vorsi.astype(float)


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
    vorsi_window: int = 14,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    VoRSI (0-100, 50=neutral) is rescaled to [-1,+1] around its midline
    and used directly as a sizing dial (already naturally bounded, no
    z-score/tanh needed), within an SMA(trend_window) uptrend gate.
    """
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    trend_long = close > close.rolling(trend_window).mean()

    vorsi = _compute_vorsi(close, volume, vorsi_window)
    dial = ((vorsi - 50.0) / 50.0).clip(lower=-1.0, upper=1.0)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    vorsi_window: int = 14,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        vorsi_window=vorsi_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
