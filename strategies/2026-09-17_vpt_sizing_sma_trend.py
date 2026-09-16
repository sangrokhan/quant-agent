"""Strategy: Volume Price Trend (VPT) as a CONTINUOUS SIZING dial within an
SMA(trend_window) uptrend gate, leverage-cap-aware for crypto.

Hypothesis (this cron trigger, iteration 4):
This repo has exactly one prior VPT entry (2026-09-05-076): a BINARY
signal-line-crossover trigger (long when VPT crosses above its own rolling
signal-line average, gated by close>SMA(trend_window)) -- accepted QQQ only,
rejected SPY (Sharpe/txcost) and crypto (decisive grid fail 0/36).

Per Investopedia's VPT explainer (https://www.investopedia.com/terms/v/vptindicator.asp,
read this iteration): "VPT gives more weight to larger price moves ... VPT
adjusts volume by the percentage price change, enhancing the analysis of
price momentum" -- i.e. VPT is fundamentally a CONTINUOUS momentum/pressure
quantity (cumulative volume-weighted pct-price-change), not naturally a
binary on/off signal. This iteration follows this repo's established
"binary threshold/crossover -> continuous sizing dial" rescue pattern
(successful previously for DPO, Hurst, VHF, TII, RVI, MAMA-FAMA spread,
Kalman slope, CBOE SKEW, Ichimoku Kumo-distance, Demand Index, Intraday
Intensity Index, etc.): instead of a discrete crossover trigger, VPT's own
short-window rate-of-change (a proxy for how fast buying/selling pressure is
building) is rolling z-scored and tanh-squashed into a continuous exposure
dial, applied within an SMA(trend_window) uptrend gate with a deadband.
First VPT-as-continuous-sizing-dial strategy in this repo -- distinct from
the existing binary VPT-signal-line-crossover entry (2026-09-05-076), which
this iteration attempts to rescue/generalize (esp. for SPY and crypto, which
failed the binary form).

Source: https://www.investopedia.com/terms/v/vptindicator.asp (VPT formula
and momentum-strength interpretation), read via browser_exec this iteration
(web_search's DuckDuckGo backend intermittently erroring/returning no
results this run; browser_exec Google SERP fallback used throughout).

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


def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
    raw = raw_exposure.fillna(0.0).to_numpy()
    held = np.zeros_like(raw)
    current = 0.0
    for i, r in enumerate(raw):
        if abs(r - current) > deadband:
            current = r
        held[i] = current
    return pd.Series(held, index=raw_exposure.index)


def _vpt(close: pd.Series, volume: pd.Series) -> pd.Series:
    """Cumulative Volume Price Trend: VPT_t = VPT_{t-1} + volume_t * pct_change_t."""
    pct_change = close.pct_change().fillna(0.0)
    return (volume * pct_change).cumsum()


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    vpt_roc_window: int = 20,
    zscore_window: int = 126,
    sensitivity: float = 0.6,
    base_exposure: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    dial = tanh(zscore(VPT.diff(vpt_roc_window), zscore_window)) -- a rising
    rate-of-change in VPT (accelerating volume-weighted buying pressure)
    pushes the dial positive (increase exposure); a falling/negative VPT ROC
    pushes it negative (reduce exposure), gated to 0 whenever close is below
    its SMA(trend_window).
    """
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    trend_long = close > close.rolling(trend_window).mean()

    vpt = _vpt(close, volume)
    vpt_roc = vpt.diff(vpt_roc_window)

    roll_mean = vpt_roc.rolling(zscore_window).mean()
    roll_std = vpt_roc.rolling(zscore_window).std(ddof=0)
    z = (vpt_roc - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = np.tanh(z.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    vpt_roc_window: int = 20,
    zscore_window: int = 126,
    sensitivity: float = 0.6,
    base_exposure: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        vpt_roc_window=vpt_roc_window,
        zscore_window=zscore_window,
        sensitivity=sensitivity,
        base_exposure=base_exposure,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
