"""Strategy: SMA(trend_window) directional gate with continuous Ehlers
Cybernetic Oscillator sizing overlay + deadband, leverage-cap-aware for
crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
John F. Ehlers' Cybernetic Oscillator (TASC June 2025, "Making A Better
Oscillator"), per https://traders.com/Documentation/FEEDbk_docs/2025/06/TradersTips.html
(TradeStation/MetaStock EasyLanguage/formula code, fully disclosed, read via
browser_exec this iteration -- web_search DDGS backend failing this cron
trigger as usual): a two-pole highpass filter (HP, removes cycle content
longer than HPLength bars) is applied to price, then Ehlers' SuperSmoother
2-pole lowpass filter (LP, removes noise shorter than LPLength bars) is
applied to HP, and the result is scaled by its own trailing 100-bar RMS
(root-mean-square) to produce a naturally-normalized, roughly zero-centered
oscillator (CyberneticOsc = LP / RMS). Genuinely novel construction: zero
prior "Cybernetic Oscillator" entries in this repo (confirmed via
strategies_index.jsonl search for "Making A Better Oscillator"/"Cybernetic
Oscillator" this iteration).

This iteration applies the repo's established continuous-sizing-dial
reframing (successfully used for many other Ehlers oscillators: Fisher
Transform, Trendflex, Even Better Sinewave, Roofing Filter, Elegant
Oscillator, Universal Oscillator, Adaptive SuperSmoother): since the
Cybernetic Oscillator is already RMS-normalized (naturally centered ~0,
typically spanning roughly [-2, 2]), it's clipped to [-2, 2] and rescaled to
[-1, 1] directly (no separate z-score needed), then used as an exposure
sizing multiplier within an SMA(trend_window) uptrend gate with a deadband
to control turnover.

Implementation note: Ehlers' HighPass/SuperSmoother recursive filter
coefficients (a1 = exp(-1.414*pi/Period), b1 = 2*a1*cos(1.414*pi/Period),
c2 = b1, c3 = -a1^2) are implemented directly per the TASC-disclosed
formulas (both TradeStation EasyLanguage and MetaStock versions agree on
the coefficients).

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


def _highpass(price: np.ndarray, period: float) -> np.ndarray:
    """Ehlers 2-pole highpass filter (TASC June 2025 $HighPass function)."""
    n = len(price)
    a1 = np.exp(-1.414 * np.pi / period)
    b1 = 2 * a1 * np.cos(1.414 * np.pi / period)
    c2 = b1
    c3 = -a1 * a1
    c1 = (1 + c2 - c3) / 4.0

    hp = np.zeros(n)
    for i in range(n):
        if i < 3:
            hp[i] = 0.0
        else:
            hp[i] = (
                c1 * (price[i] - 2 * price[i - 1] + price[i - 2])
                + c2 * hp[i - 1]
                + c3 * hp[i - 2]
            )
    return hp


def _supersmoother(price: np.ndarray, period: float) -> np.ndarray:
    """Ehlers SuperSmoother 2-pole lowpass filter ($SuperSmoother function)."""
    n = len(price)
    a1 = np.exp(-1.414 * np.pi / period)
    b1 = 2 * a1 * np.cos(1.414 * np.pi / period)
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3

    ss = np.zeros(n)
    for i in range(n):
        if i < 3:
            ss[i] = price[i]
        else:
            ss[i] = c1 * (price[i] + price[i - 1]) / 2.0 + c2 * ss[i - 1] + c3 * ss[i - 2]
    return ss


def _cybernetic_oscillator(
    close: pd.Series, hp_length: int, lp_length: int, rms_length: int
) -> pd.Series:
    price = close.to_numpy(dtype=float)
    hp = _highpass(price, hp_length)
    lp = _supersmoother(hp, lp_length)

    lp_series = pd.Series(lp, index=close.index)
    rms = np.sqrt((lp_series ** 2).rolling(rms_length).mean())
    rms = rms.replace(0.0, np.nan)

    osc = lp_series / rms
    return osc


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
    hp_length: int = 30,
    lp_length: int = 20,
    rms_length: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    Cybernetic Oscillator is RMS-normalized (already roughly zero-centered,
    typical range [-2, 2]); clipped to [-2, 2] and rescaled to [-1, 1] as
    the sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    osc = _cybernetic_oscillator(close, hp_length, lp_length, rms_length)
    osc_dial = (osc.clip(-2.0, 2.0) / 2.0).clip(-1.0, 1.0)

    raw_exposure = base_exposure + sensitivity * osc_dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    hp_length: int = 30,
    lp_length: int = 20,
    rms_length: int = 100,
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
        hp_length=hp_length,
        lp_length=lp_length,
        rms_length=rms_length,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
