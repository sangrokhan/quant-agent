"""Strategy: SMA(trend_window) directional gate with continuous On-Balance
Volume (OBV) minus its own EMA sizing overlay + deadband, leverage-cap-aware
for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
On-Balance Volume (Joseph Granville, 1963): OBV_t = OBV_{t-1} + volume_t if
close_t > close_{t-1}; OBV_t = OBV_{t-1} - volume_t if close_t < close_{t-1};
unchanged if equal. Source: Investopedia's OBV article (confirmed formula
and cumulative construction) plus GoCharting's OBV docs (which describe
using OBV vs. its own moving average as the concrete tradeable signal).
Repo already has one prior OBV entry (2026-09-04-027: binary OBV-crosses-
above-its-own-EMA(20) confirmation signal within an SMA(200) uptrend filter
-- accepted QQQ only, SPY near-miss Sharpe 0.967, crypto rejected). This
iteration reframes the OBV-minus-its-own-EMA spread as a CONTINUOUS SIZING
dial instead of a binary crossover trigger: rolling z-scored + tanh-squashed
to [-1,1], used as a sizing multiplier within an SMA(trend_window) uptrend
gate, deadband to cut turnover, leverage_cap for crypto. This is the same
"binary crossover -> continuous sizing dial" pattern already validated for
RMI/RMO/McGinley Dynamic/Anchored Momentum in this repo, applied here to
OBV for the first time, and specifically targets rescuing the recorded SPY
near-miss from 2026-09-04-027 via smoother, less-abrupt position sizing.

Sources:
- https://www.investopedia.com/terms/o/onbalancevolume.asp (OBV formula,
  cumulative construction, "smart money" volume-leads-price rationale)
- https://gocharting.com/docs/charting/technical-indicator/oscillators/on-balance-volume
  (confirms OBV-vs-its-own-moving-average as the standard tradeable signal
  form, matching repo's prior 2026-09-04-027 implementation)

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


def _obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff().fillna(0.0))
    signed_volume = direction * volume
    return signed_volume.cumsum()


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
    obv_ema_span: int = 20,
    zscore_window: int = 100,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    OBV minus its own EMA(obv_ema_span) is rolling z-scored over
    `zscore_window` bars and tanh-squashed to [-1,+1] before use as a
    sizing dial.
    """
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    trend_long = close > close.rolling(trend_window).mean()

    obv = _obv(close, volume)
    obv_ema = obv.ewm(span=obv_ema_span, adjust=False).mean()
    diff = obv - obv_ema

    roll_mean = diff.rolling(zscore_window).mean()
    roll_std = diff.rolling(zscore_window).std()
    zscore = (diff - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(zscore.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    obv_ema_span: int = 20,
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
        obv_ema_span=obv_ema_span,
        zscore_window=zscore_window,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
