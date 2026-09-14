"""Strategy: SMA(trend_window) directional gate with continuous Waddah
Attar Explosion (WAE) sizing overlay + deadband, leverage-cap-aware for
crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Waddah Attar Explosion (WAE), per LuxAlgo's library doc
(https://www.luxalgo.com/library/indicator/waddah-attar-explosion/,
formula also already fully confirmed by this repo's 3 prior binary-trigger
entries: 2026-09-06-104, 2026-09-10-082, 2026-09-10-092): trend_power =
bar-to-bar change of a 20/40 EMA MACD line, scaled by sensitivity=150;
explosion_line = width of a 20-period, 2-std Bollinger Band; dead_zone =
ATR(100)*3.7 noise floor. All 3 prior repo entries used trend_power vs
explosion_line/dead_zone as a BINARY momentum-volatility-compound GATE for
discrete breakout entries (accepted SPY-only, QQQ near-miss retuned but
never crypto-tested for the binary version). This iteration instead
reframes trend_power itself (a naturally signed, unbounded MACD-change
series) as a CONTINUOUS SIZING dial: rolling z-scored and tanh-squashed to
[-1,+1] within an SMA(trend_window) uptrend gate -- the same "unbounded
diff -> z-score -> tanh" reframing pattern already used successfully for
TCF, Precision Trend, DSP, and Voss earlier this cron trigger. First WAE
continuous-sizing variant (3 prior binary breakout-gate variants).
Economic rationale: a continuous dial captures HOW MUCH momentum is
clearing the volatility envelope (not just a binary yes/no explosion
event), which should reduce whipsaw around the gate threshold that likely
hurt the binary version's QQQ config.

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


def _wae_trend_power(
    close: pd.Series, fast_len: int, slow_len: int, sensitivity: float
) -> pd.Series:
    """WAE trend_power: bar-to-bar change of the (fast-slow) EMA MACD line,
    scaled by sensitivity. Naturally signed and unbounded."""
    macd_line = close.ewm(span=fast_len, adjust=False).mean() - close.ewm(
        span=slow_len, adjust=False).mean()
    trend_power = macd_line.diff() * sensitivity
    return trend_power.fillna(0.0)


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
    fast_len: int = 20,
    slow_len: int = 40,
    sensitivity_scale: float = 150.0,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    WAE trend_power (fast/slow EMA MACD-change, scaled) is rolling
    z-scored over `zscore_window` bars and tanh-squashed to [-1,+1] before
    use as a sizing dial, within an SMA(trend_window) uptrend gate.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    trend_power = _wae_trend_power(close, fast_len, slow_len, sensitivity_scale)

    roll_mean = trend_power.rolling(zscore_window).mean()
    roll_std = trend_power.rolling(zscore_window).std()
    zscore = (trend_power - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    fast_len: int = 20,
    slow_len: int = 40,
    sensitivity_scale: float = 150.0,
    zscore_window: int = 100,
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
        fast_len=fast_len,
        slow_len=slow_len,
        sensitivity_scale=sensitivity_scale,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
