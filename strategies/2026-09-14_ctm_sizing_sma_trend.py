"""Strategy: SMA(trend_window) directional gate with continuous Chande
Trend Meter (CTM) composite sizing overlay + deadband, leverage-cap-aware
for crypto from the start.

Hypothesis (knowledge_base id TBD, this cron trigger):
Chande Trend Meter (CTM, Tushar Chande), per StockCharts ChartSchool
(formula already fully confirmed and reused verbatim from this repo's
existing accepted strategy strategies/2026-09-11_chande_trend_meter_ctm.py,
no fresh web fetch needed this sub-step): a 0-100 composite trend-strength
score combining (1) Bollinger %B averaged across FOUR timeframes
(20/50/75/100-day), (2) price change relative to its own 100-day std dev
(squashed to [0,1]), (3) RSI(14) rescaled to [0,1], and (4) a 2-day
price-channel breakout flag (1/0.5/0). This repo's only prior CTM entries
(2026-09-11-033/067) used the composite score as a binary threshold
CROSSOVER entry trigger (entry_threshold=60/exit_threshold, accepted
QQQ+SPY at a fine-tuned shared config, crypto rejected decisively). This
iteration reframes CTM as a CONTINUOUS SIZING dial within an
SMA(trend_window) uptrend gate -- the same reframing pattern that rescued
Firefly Oscillator, Elegant Oscillator, Volume RSI, and Trend Continuation
Factor earlier this same cron trigger. Economic rationale: CTM already
blends 4 independent trend/momentum signals into one composite reading;
using its raw 0-100 value directly as a continuous sizing dial (rather
than thresholding for discrete entries) lets exposure track the combined
strength/conviction of that composite continuously within an established
uptrend, rather than only reacting to a single crossing level. First CTM
continuous-sizing variant.

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


def _pct_b(close: pd.Series, window: int, num_std: float = 2.0) -> pd.Series:
    """Bollinger %B: 0 = at lower band, 1 = at upper band (clipped to [0,1])."""
    sma = close.rolling(window).mean()
    std = close.rolling(window).std()
    upper = sma + num_std * std
    lower = sma - num_std * std
    pct_b = (close - lower) / (upper - lower).replace(0.0, float("nan"))
    return pct_b.clip(0.0, 1.0)


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, float("nan"))
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    return rsi


def _compute_ctm(df: pd.DataFrame) -> pd.Series:
    close = df["close"]
    high = df["high"] if "high" in df.columns else close
    low = df["low"] if "low" in df.columns else close

    bb_component = pd.concat(
        [_pct_b(close, w) for w in (20, 50, 75, 100)], axis=1
    ).mean(axis=1)

    std100 = close.rolling(100).std()
    price_chg_z = (close - close.shift(100)) / std100.replace(0.0, float("nan"))
    z_component = (price_chg_z / 4.0 + 0.5).clip(0.0, 1.0)

    rsi_component = (_rsi(close, 14) / 100.0).clip(0.0, 1.0)

    ch_high = high.shift(1).rolling(2).max()
    ch_low = low.shift(1).rolling(2).min()
    breakout_component = pd.Series(0.5, index=close.index)
    breakout_component = breakout_component.where(close <= ch_high, 1.0)
    breakout_component = breakout_component.where(close >= ch_low, 0.0)

    composite = (bb_component + z_component + rsi_component + breakout_component) / 4.0
    ctm = (composite * 100.0).clip(0.0, 100.0)
    return ctm


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
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    CTM (0-100, 50=neutral by construction) is rescaled to [-1,+1] around
    its midline and used directly as a sizing dial, within an
    SMA(trend_window) uptrend gate.
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    ctm = _compute_ctm(df)
    dial = ((ctm - 50.0) / 50.0).clip(lower=-1.0, upper=1.0)

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
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
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
