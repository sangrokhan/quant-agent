"""Strategy: SMA(trend_window) directional gate with continuous William Blau
Ergodic Oscillator sizing overlay + deadband, leverage-cap-aware for crypto
from the start.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
William Blau's Ergodic Oscillator (double-smoothed momentum ratio: one-bar
price change passed through a long-length then short-length EMA, divided by
the identical pipeline applied to the absolute change, scaled to +/-100 by
construction) has only ever been tested in this repo as a BINARY
signal-line-crossover entry (2026-09-06-102, REJECTED — LuxAlgo's own
"Zero crosses: net double-smoothed momentum changing sign, the slower
trend-change cue" framing plus this cron trigger's repeatedly-validated
pattern (Coppock/AO/BW-MFI/TSI/SMI/DSS all flipped from binary
threshold/crossover rejects to accepted QQQ-only CONTINUOUS sizing dials)
motivates reframing the Ergodic line itself as a bounded-ish [-100,+100]
continuous exposure dial within an SMA(trend_window) uptrend gate, instead
of a discrete signal-line cross entry/exit.

Source: https://www.luxalgo.com/library/indicator/ergodic-oscillator/
(re-confirmed this iteration; same source as the already-tested binary
2026-09-06-102 entry — this iteration only changes the *use* of the
indicator, not its formula).

Construction (identical formula to 2026-09-06-102):
    diff = close.diff(1)
    num = EMA(EMA(diff, long_len), short_len)
    den = EMA(EMA(|diff|, long_len), short_len)
    Ergodic = 100 * num / den   (empirically bounded roughly [-100, +100],
    not strictly, since den can be small; clipped defensively)

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


def _ergodic(close: pd.Series, long_len: int, short_len: int) -> pd.Series:
    diff = close.diff(1)
    num = diff.ewm(span=long_len, adjust=False).mean().ewm(span=short_len, adjust=False).mean()
    den = diff.abs().ewm(span=long_len, adjust=False).mean().ewm(span=short_len, adjust=False).mean()
    den = den.replace(0.0, np.nan)
    ergodic = 100.0 * (num / den)
    return ergodic.fillna(0.0).clip(lower=-100.0, upper=100.0)


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
    long_len: int = 20,
    short_len: int = 5,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Ergodic is empirically bounded roughly [-100,100]; rescaled to
    [-1,+1] via /100, then used directly as a sizing dial within the
    SMA(trend_window) uptrend gate.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    ergodic = _ergodic(close, long_len, short_len)
    ergodic_centered = (ergodic / 100.0).clip(lower=-1.0, upper=1.0)

    raw_exposure = base_exposure + sensitivity * ergodic_centered
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    long_len: int = 20,
    short_len: int = 5,
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
        long_len=long_len,
        short_len=short_len,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
