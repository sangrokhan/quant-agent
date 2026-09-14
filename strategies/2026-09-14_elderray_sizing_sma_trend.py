"""Strategy: SMA(trend_window) directional gate with continuous Elder-Ray
Net Power (ATR-normalized Bull Power minus Bear Power) sizing overlay +
deadband.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
Elder-Ray Index (Dr. Alexander Elder, 1989; formula per
https://www.investopedia.com/terms/e/elderray.asp, read this iteration via
browser_exec fallback -- web_search's DuckDuckGo backend TLS-errored on
every query attempted this iteration): 13-period EMA as a "consensus of
value" baseline; Bull Power = High - EMA (buyers' ability to push price
above consensus), Bear Power = Low - EMA (sellers' ability to push price
below consensus). Source's own guidance: "consider long positions if the
bull power is rising, bear power is in negative territory and rising
(getting weaker), and EMA is sloping upward."

This repo has 8 prior Elder-Ray entries (2026-09-04-037, -110, 2026-09-06-135,
-138 [A/D not Elder-Ray], -176, 2026-09-08-008, -155, 2026-09-09-104), ALL
using Bull/Bear Power as a binary divergence/crossover/contraction-recovery
ENTRY trigger -- all rejected (Sharpe/TC-survival misses, near-miss at best
on 2026-09-06-135/176). None reframed Elder-Ray as a CONTINUOUS SIZING dial,
the pattern that has repeatedly rescued other previously-rejected binary
oscillators this cron trigger (CMO, Ultimate Oscillator, StochRSI, MFI,
CMF, Aroon, Williams %R, %B, DMI-diff, ADX, CHOP, ER, TRIX, TSI, R2 -- all
accepted QQQ(+SPY), rejected crypto once reframed as continuous dials with
a deadband).

Unlike those oscillators, raw Bull/Bear Power are NOT natively bounded
(dollar-scale, price-dependent) -- so this iteration ATR-normalizes them
first: net_power = (BullPower - BearPower) / ATR(atr_window), which
rescales the Elder-Ray net-power spread into an approximately stationary,
roughly-bounded unit comparable across symbols/regimes (same normalization
trick this repo already used for VAMA/STARC/Keltner-family ATR bands).
Within an SMA(trend_window) uptrend gate, exposure scales up as ATR-
normalized net buying pressure strengthens and toward the base level as it
fades, rather than using Bull/Bear Power crossovers/divergence as a hard
binary trigger -- directly testing whether Elder-Ray's repeated binary-
signal rejections were about the ENTRY-TRIGGER construction (as with the
oscillators above) rather than Elder-Ray itself lacking predictive content.

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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
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
    return tr.rolling(window).mean()


def _elder_ray_net_power(df: pd.DataFrame, ema_window: int, atr_window: int) -> pd.Series:
    """ATR-normalized Elder-Ray net power: (BullPower - BearPower) / ATR.

    BullPower = High - EMA(close, ema_window); BearPower = Low - EMA(close,
    ema_window). Normalizing the dollar-scale spread by ATR converts it
    into a roughly stationary, cross-symbol-comparable unit (typically in
    the +/-3 range for a trending market, occasionally wider in extreme
    regimes) -- NOT hard-bounded like RSI/CCI/CMO, so a light clip is
    applied downstream before use as a sizing multiplier.
    """
    ema = df["close"].ewm(span=ema_window, adjust=False).mean()
    bull_power = df["high"] - ema
    bear_power = df["low"] - ema
    atr = _atr(df, atr_window)
    net_power = (bull_power - bear_power) / atr.replace(0, np.nan)
    return net_power


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
    ema_window: int = 13,
    atr_window: int = 14,
    net_power_reference: float = 2.0,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    net_power = _elder_ray_net_power(df, ema_window=ema_window, atr_window=atr_window)
    net_power_norm = (net_power / net_power_reference).clip(lower=-1.5, upper=1.5)

    raw_exposure = base_exposure + sensitivity * net_power_norm
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    ema_window: int = 13,
    atr_window: int = 14,
    net_power_reference: float = 2.0,
    base_exposure: float = 0.5,
    sensitivity: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.10,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        ema_window=ema_window,
        atr_window=atr_window,
        net_power_reference=net_power_reference,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
