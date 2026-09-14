"""Strategy: SMA(trend_window) directional gate combined with a continuous
Damiani Volatmeter "trade / no-trade" volatility-regime dial as an exposure
multiplier.

Hypothesis (knowledge_base id 2026-09-15-032, this cron trigger):
Damiani Volatmeter (Luis Damiani), per
https://www.google.com/search?q=Damiani+Volatmeter+indicator+formula+trading
(AI overview) and https://www.tradingview.com/script/z95IdM4a-Damiani-Volatmeter-loxx/
(loxx variant description), visited this iteration:
  ATR ratio (vol line)   = ATR(fast_len) / ATR(slow_len)
  StDev ratio (anti-thr) = StDev(close, fast_len) / StDev(close, slow_len)
  threshold               = threshold_const - StDev_ratio
  vol_line (with lag suppressor) = ATR_ratio + lag_k * (ATR_ratio.shift(1) - ATR_ratio.shift(3))

The indicator's own trading rule (per the loxx TradingView description) is
binary-ish: "you only take trades when volatility is high/rising (vol_line
above threshold, i.e. green), and stay flat when volatility is low/ranging
(vol_line below threshold + a recharge minimum, i.e. red)". Volatility
itself carries no direction -- direction must come from a separate trend
filter, which loxx's own writeup explicitly recommends pairing with (they
suggest Fisher Transform/Gaussian filters; this repo already has an
SMA-trend-gate pattern validated many times this cron trigger, reused here
for consistency and because it's a simpler, already-proven directional
filter).

This is a genuinely new indicator family for this repo (0 prior
strategies/log entries reference "Damiani" or "Volatmeter"). Implemented as
a continuous sizing dial (tanh-squashed distance of vol_line above the
dynamic threshold, scaled into [0, leverage_cap]) rather than the strictly
binary trade/no-trade rule, following this cron trigger's established
pattern of turning discrete volatility/oscillator filters into continuous
dials to avoid the signal-sparsity failure mode seen repeatedly with hard
threshold+crossover rules in this repo's log (e.g. WaveTrend 2026-09-04-145
/2026-09-08-094/2026-09-09-055, rescued by the same continuous-dial
transform in 2026-09-15-031).

Economic rationale: trend-following strategies whipsaw in low-volatility
chop and only pay off during genuine trending/high-volatility expansions;
using a volatility-regime dial to scale exposure up when realized
volatility is expanding relative to its recent past (and down/to zero when
compressed) should reduce whipsaw drag while preserving upside during
trend regimes, similar in spirit to a vol-breakout filter but built from
Damiani's specific ATR-ratio/StDev-ratio/threshold construction rather than
a raw ATR percentile.

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
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _damiani_vol_line(
    df: pd.DataFrame,
    fast_len: int,
    slow_len: int,
    threshold_const: float,
    lag_k: float,
) -> tuple[pd.Series, pd.Series]:
    """Return (vol_line, threshold) per the Damiani Volatmeter construction."""
    close = df["close"]
    tr = _true_range(df)
    atr_fast = tr.rolling(fast_len).mean()
    atr_slow = tr.rolling(slow_len).mean()
    atr_ratio = atr_fast / atr_slow.replace(0.0, np.nan)

    lag_term = lag_k * (atr_ratio.shift(1) - atr_ratio.shift(3))
    vol_line = atr_ratio + lag_term.fillna(0.0)

    std_fast = close.rolling(fast_len).std()
    std_slow = close.rolling(slow_len).std()
    std_ratio = std_fast / std_slow.replace(0.0, np.nan)
    threshold = threshold_const - std_ratio

    return vol_line, threshold


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
    fast_len: int = 13,
    slow_len: int = 40,
    threshold_const: float = 1.4,
    lag_k: float = 0.5,
    dial_scale: float = 3.0,
    base_exposure: float = 0.4,
    sensitivity: float = 0.6,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    The Damiani vol_line minus its dynamic threshold is scaled by
    `dial_scale` and tanh-squashed to [-1, +1] as a volatility-regime sizing
    dial (positive = volatility expanding above threshold, "tradeable";
    negative = compressed/ranging, "avoid"), gated by an SMA(trend_window)
    uptrend filter for direction (volatility itself has no direction).
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    vol_line, threshold = _damiani_vol_line(df, fast_len, slow_len, threshold_const, lag_k)

    vol_signal = (vol_line - threshold) * dial_scale
    dial = np.tanh(vol_signal.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    fast_len: int = 13,
    slow_len: int = 40,
    threshold_const: float = 1.4,
    lag_k: float = 0.5,
    dial_scale: float = 3.0,
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
        threshold_const=threshold_const,
        lag_k=lag_k,
        dial_scale=dial_scale,
        base_exposure=base_exposure,
        sensitivity=sensitivity,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
