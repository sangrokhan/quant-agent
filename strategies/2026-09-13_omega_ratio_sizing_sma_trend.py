"""Strategy: SMA200 trend-following gate with rolling Omega-ratio dynamic
exposure scaling.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per https://en.wikipedia.org/wiki/Omega_ratio (Keating & Shadwick 2002,
read via browser_exec this iteration), the Omega ratio is a probability-
weighted ratio of gains versus losses relative to a threshold return
theta: Omega(theta) = E[(r-theta)+] / E[(theta-r)+] -- the average upside
beyond theta divided by the average downside below theta. Unlike the
Sharpe ratio (which only uses the first two moments -- mean and variance),
Omega considers the ENTIRE return distribution (all moments, including
skew and kurtosis). This strategy tests whether scaling an SMA(200)
trend-following gate's exposure by the underlying asset's own trailing
Omega ratio (at theta=0, the Bernardo-Ledoit gain-loss-ratio special case)
produces a more effective sizing signal than the repo's existing
sizing overlays (inverse-vol, CVaR, MAR-ratio, downside-deviation) --
because Omega captures distributional shape (fat tails, skew) that none
of those single-statistic risk measures fully capture. First Omega-ratio-
based strategy (entry OR sizing) in this repo.

Signal logic
------------
- Base directional signal: long when close > SMA(trend_window), flat
  otherwise (identical trend gate to the repo's other sizing-overlay
  strategies, isolating the sizing-mechanism variable).
- Rolling Omega ratio (theta=0) over `omega_window` days of daily returns:
  Omega = mean(positive returns clipped at 0) / mean(abs(negative returns
  clipped at 0)) -- i.e. average gain magnitude / average loss magnitude
  weighted by their full occurrence (not just win rate).
- Exposure: scale = clip(omega / omega_reference, 0, leverage_cap), where
  omega_reference is a normalizing constant (Omega ratio level mapping to
  full 1.0x exposure; Omega=1.0 is break-even, so omega_reference is set
  above 1.0 by default to require a genuine edge before sizing up).
  Applied only while the trend gate is long.

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


def _rolling_omega_ratio(daily_ret: pd.Series, window: int) -> pd.Series:
    """Rolling discrete Omega ratio (theta=0): mean of positive returns
    divided by mean absolute value of negative returns, vectorized via
    numpy sliding windows."""
    values = daily_ret.to_numpy(dtype=float)
    n = len(values)
    out = np.full(n, np.nan)
    if n < window:
        return pd.Series(out, index=daily_ret.index)

    windows = np.lib.stride_tricks.sliding_window_view(values, window)
    gains = np.maximum(windows, 0.0)
    losses = np.maximum(-windows, 0.0)
    with np.errstate(invalid="ignore"):
        mean_gain = np.nanmean(gains, axis=1)
        mean_loss = np.nanmean(losses, axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        omega = np.where(mean_loss > 1e-12, mean_gain / mean_loss, np.nan)

    out[window - 1:] = omega
    return pd.Series(out, index=daily_ret.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    omega_window: int = 60,
    omega_reference: float = 1.2,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    daily_ret = close.pct_change()
    omega = _rolling_omega_ratio(daily_ret, omega_window)

    raw_exposure = (omega / omega_reference).astype(float)
    exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap).fillna(0.0)

    position = exposure.where(trend_long.fillna(False), other=0.0)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
