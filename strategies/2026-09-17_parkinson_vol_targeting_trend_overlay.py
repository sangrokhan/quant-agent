"""Strategy: Inverse-Parkinson-volatility position-sizing overlay on a plain
SMA trend signal.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per https://ryanoconnellfinance.com (Range Volatility Calculator page) and
https://quantra.quantinsti.com/glossary/Estimating-volatility-using-Parkinson-
estimator (both read via browser_exec Google-SERP-snippet fallback this
iteration -- web_search's DDGS backend returned empty/garbage results for
this query), the Parkinson (1980) high-low range volatility estimator,

    sigma_Parkinson^2 = (1 / (4 * n * ln(2))) * sum( ln(H_t/L_t)^2 )

uses each bar's own high-low range rather than only the close-to-close
return, and is reported to be roughly 5x more statistically efficient
(lower estimation variance for the same sample size) than the standard
close-to-close realized-vol estimator because it captures the maximum
intraday/inter-bar price excursion rather than a single point sample.

This repo already tested inverse-volatility position-sizing using
close-to-close trailing realized vol as the denominator (id 2026-09-08-165,
strategies/2026-09-08_vol_targeting_trend_overlay.py: accepted equity-only,
QQQ Sharpe 1.327, SPY narrow pass 1.016, crypto rejected decisively 0/36).
This iteration swaps ONLY the volatility ESTIMATOR feeding the identical
target-vol/estimated-vol sizing formula and identical SMA(trend_window)
trend gate -- from close-to-close realized vol to the Parkinson range-based
estimator -- to test whether the reported efficiency gain (using
information the close-to-close estimator discards: the daily high/low
range) translates into a smoother, more responsive vol-target sizing dial
and better risk-adjusted performance / broader (e.g. crypto) applicability
than the close-to-close version. Distinct from all prior range-based
volatility estimator strategies in this repo (Garman-Klass squeeze-breakout
2026-09-08-023/044, Yang-Zhang regime gate 2026-09-10-087, Parkinson
expansion-cross/compression-reversion pair 2026-09-09-027/028) since none
of those used a range-based estimator as an inverse-vol-TARGETING SIZING
denominator -- they all used it as a directional entry trigger or regime
gate, not as the position-size scaling denominator.

Signal logic
------------
- Trend gate: close > SMA(trend_window) -> want to be long, else flat.
- When long, size the position as
  exposure = min(target_vol / parkinson_vol, leverage_cap), using ONLY
  trailing (non-look-ahead) Parkinson range volatility over vol_window
  days, annualized.
- Both the trend gate and Parkinson vol estimate use data available
  strictly before the trading day (exposure shifted by 1 bar in
  generate_returns, same convention as every other strategy in this repo).
- Exposure floor of 0 when flat trend; no shorting.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap], not strictly {0,1}, since the sizing mechanism
    itself is the object of the hypothesis).
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


def _parkinson_vol(high: pd.Series, low: pd.Series, vol_window: int) -> pd.Series:
    """Rolling annualized Parkinson (1980) high-low range volatility.

    Per-bar variance contribution: (1/(4*ln(2))) * ln(H/L)^2
    Rolled over `vol_window` bars, averaged, then annualized (sqrt(252)).
    """
    safe_high = high.where(high > 0)
    safe_low = low.where(low > 0)
    log_hl = np.log(safe_high / safe_low)
    per_bar_var = (log_hl ** 2) / (4.0 * np.log(2.0))
    rolling_var = per_bar_var.rolling(vol_window, min_periods=vol_window).mean()
    return np.sqrt(rolling_var) * np.sqrt(252.0)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    vol_window: int = 20,
    target_vol: float = 0.15,
    leverage_cap: float = 1.5,
) -> pd.Series:
    """Return a continuous target-exposure series in [0, leverage_cap]."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    sma = close.rolling(trend_window).mean()
    trend_long = close > sma

    parkinson_vol = _parkinson_vol(high, low, vol_window)
    safe_vol = parkinson_vol.clip(lower=1e-4)
    raw_exposure = (target_vol / safe_vol).clip(upper=leverage_cap)

    exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)
    exposure = exposure.fillna(0.0).clip(lower=0.0, upper=leverage_cap)
    return exposure


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    # Shift exposure by 1 day: yesterday's signal/sizing determines today's
    # return exposure (avoid look-ahead bias).
    strategy_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
