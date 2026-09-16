"""Strategy: Inverse-Rogers-Satchell-volatility position-sizing overlay on a
plain SMA trend signal.

Hypothesis (knowledge_base id TBD, this cron trigger, 4th iteration):
Per https://ryanoconnellfinance.com/historical-volatility-estimators (read
via browser_exec Google-SERP-snippet fallback this iteration -- web_search's
DDGS backend errored with a TLS "peer closed connection" RequestError on
the direct query), the Rogers-Satchell (1991) OHLC volatility estimator,

    sigma^2_RS = (1/n) * sum[ ln(H/C)*ln(H/O) + ln(L/C)*ln(L/O) ]

is the standard range-based volatility measure explicitly designed to be
DRIFT-INDEPENDENT: unlike Parkinson and Garman-Klass (which assume
zero-drift Brownian motion and can be biased in trending markets),
Rogers-Satchell stays unbiased when the underlying price has a non-zero
drift/trend (it does not, however, handle overnight opening jumps).

This repo has now tested three vol estimators as inverse-vol-TARGETING
SIZING dials on the identical SMA-trend-gate + deadband construction this
same cron trigger: close-to-close (2026-09-08-165, pre-existing, accepted
equity-only), Parkinson (2026-09-17-050/051, accepted QQQ+SPY+BTC/USDT),
Garman-Klass (2026-09-17-052, accepted QQQ+SPY+BTC/USDT, strongest crypto
result of the three). This iteration is the 4th and final planned
estimator-swap variant for this specific research thread this trigger:
Rogers-Satchell is economically distinct from the prior three specifically
because our strategy signal itself is a TRENDING (SMA-gated, drift-positive
by construction whenever active) signal -- so a volatility estimator
explicitly designed to stay unbiased under drift is arguably the most
theoretically well-matched sizing denominator for this exact use case,
whereas Parkinson/Garman-Klass's zero-drift assumption is technically
violated by the very trending regime the strategy trades in. Distinct from
this repo's own prior standalone-Rogers-Satchell novelty screening
(2026-09-10-088, correctly noted no DISTINCT standalone entry-trigger rule
existed at the time) since this is a sizing-DIAL application, matching the
pattern already validated for the other three estimators.

Signal logic
------------
- Trend gate: close > SMA(trend_window) -> want to be long, else flat.
- When long, size the position as
  exposure = min(target_vol / rogers_satchell_vol, leverage_cap), using
  ONLY trailing (non-look-ahead) Rogers-Satchell volatility over
  vol_window days, annualized.
- Rebalance-buffer deadband: hold exposure constant unless the new target
  differs from the last held value by more than `deadband`.
- Both the trend gate and RS vol estimate use data available strictly
  before the trading day (exposure shifted by 1 bar in generate_returns).

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


def _rogers_satchell_vol(
    open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series,
    vol_window: int,
) -> pd.Series:
    """Rolling annualized Rogers-Satchell (1991) drift-independent
    OHLC volatility.

    Per-bar variance term: ln(H/C)*ln(H/O) + ln(L/C)*ln(L/O)
    (always >= 0 by construction, no drift-correction subtraction needed
    unlike Garman-Klass).
    """
    safe_open = open_.where(open_ > 0)
    safe_high = high.where(high > 0)
    safe_low = low.where(low > 0)
    safe_close = close.where(close > 0)

    per_bar_var = (
        np.log(safe_high / safe_close) * np.log(safe_high / safe_open)
        + np.log(safe_low / safe_close) * np.log(safe_low / safe_open)
    )
    rolling_var = per_bar_var.rolling(vol_window, min_periods=vol_window).mean()
    rolling_var = rolling_var.clip(lower=0.0)
    return np.sqrt(rolling_var) * np.sqrt(252.0)


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
    trend_window: int = 200,
    vol_window: int = 20,
    target_vol: float = 0.15,
    leverage_cap: float = 1.5,
    deadband: float = 0.15,
) -> pd.Series:
    """Return a continuous target-exposure series in [0, leverage_cap],
    deadband-held to control turnover."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    high = df["high"]
    low = df["low"]

    sma = close.rolling(trend_window).mean()
    trend_long = close > sma

    rs_vol = _rogers_satchell_vol(open_, high, low, close, vol_window)
    safe_vol = rs_vol.clip(lower=1e-4)
    raw_exposure = (target_vol / safe_vol).clip(upper=leverage_cap)

    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)
    raw_exposure = raw_exposure.fillna(0.0).clip(lower=0.0, upper=leverage_cap)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
