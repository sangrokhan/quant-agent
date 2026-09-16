"""Strategy: Inverse-Garman-Klass-volatility position-sizing overlay on a
plain SMA trend signal.

Hypothesis (knowledge_base id TBD, this cron trigger, 3rd iteration):
Per https://faintrading.com/formulas/garman-klass (read via browser_exec
this iteration -- web_extract's configured backend is search-only/cannot
fetch page content; web_search itself worked fine for keyword discovery),
the Garman & Klass (1980) OHLC volatility estimator,

    sigma^2 = (0.5/n) * sum(ln(H_i/L_i)^2) - (2*ln(2)-1)/n * sum(ln(C_i/C_(i-1))^2)

combines the high-low range term (like Parkinson) with an open/close-drift
correction term, and is reported ~7.4-8x more statistically efficient than
the plain close-to-close estimator (vs Parkinson's ~5x) because it partially
corrects the bias Parkinson picks up when the closing price drifts within
the bar.

This repo has tested Garman-Klass twice before (2026-09-08-023/044:
volatility-percentile-rank compression-BREAKOUT entry TRIGGER, both
rejected -- full-sample Sharpe near-miss 0.80, crypto decisive 0/36) and
tested the SAME sizing-overlay CONSTRUCTION with two OTHER estimators this
same cron trigger (close-to-close: id 2026-09-08-165 pre-existing accepted
equity-only; Parkinson: id 2026-09-17-050/051 this trigger, accepted
QQQ+SPY+BTC/USDT with deadband). This iteration is the first to apply the
inverse-vol-TARGETING SIZING construction (not a compression/breakout
entry trigger) to Garman-Klass specifically -- testing whether GK's
reported extra statistical efficiency over Parkinson (7.4-8x vs ~5x, per
the same efficiency-ranking literature) translates into an even better
sizing-dial signal, and building in the deadband from the start (learned
directly from this trigger's own 050->051 turnover-cost lesson, rather than
re-discovering it via a second sub-iteration).

Signal logic
------------
- Trend gate: close > SMA(trend_window) -> want to be long, else flat.
- When long, size the position as
  exposure = min(target_vol / garman_klass_vol, leverage_cap), using ONLY
  trailing (non-look-ahead) Garman-Klass volatility over vol_window days,
  annualized.
- Rebalance-buffer deadband: hold exposure constant unless the new target
  differs from the last held value by more than `deadband` (turnover
  control, per this trigger's own 2026-09-17-050->051 lesson).
- Both the trend gate and GK vol estimate use data available strictly
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


def _garman_klass_vol(
    open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series,
    vol_window: int,
) -> pd.Series:
    """Rolling annualized Garman-Klass (1980) OHLC volatility.

    Per-bar variance term:
        0.5 * ln(H/L)^2 - (2*ln(2)-1) * ln(C/C_prev)^2
    (the open_ argument is accepted for interface symmetry/future extension
    but the classic GK formula as sourced only uses H, L, C, C_prev.)
    """
    del open_  # not used by the classic GK formula as sourced this iteration
    safe_high = high.where(high > 0)
    safe_low = low.where(low > 0)
    safe_close = close.where(close > 0)
    prev_close = safe_close.shift(1)

    hl_term = 0.5 * (np.log(safe_high / safe_low) ** 2)
    co_term = (2.0 * np.log(2.0) - 1.0) * (np.log(safe_close / prev_close) ** 2)
    per_bar_var = hl_term - co_term

    rolling_var = per_bar_var.rolling(vol_window, min_periods=vol_window).mean()
    rolling_var = rolling_var.clip(lower=0.0)  # GK var can dip slightly negative on some bars
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
    open_ = df["open"] if "open" in df.columns else close
    high = df["high"]
    low = df["low"]

    sma = close.rolling(trend_window).mean()
    trend_long = close > sma

    gk_vol = _garman_klass_vol(open_, high, low, close, vol_window)
    safe_vol = gk_vol.clip(lower=1e-4)
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
