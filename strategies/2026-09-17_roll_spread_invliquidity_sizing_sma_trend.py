"""Strategy: SMA(trend_window) trend-following gate with continuous
Roll's (1984) implied bid-ask spread estimator used as an INVERSE-LIQUIDITY
sizing dial.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per Roll, R. (1984) "A Simple Implicit Measure of the Effective Bid-Ask
Spread in an Efficient Market" (formula cross-confirmed via
metricgate.com/Finance, a TradingView PickMyTradeLib script description,
Pineify's bid-ask-bounce writeup, and Bernt Arne Odegaard's teaching slides
ba-odegaard.no/teach/notes/roll_slides -- all read via browser_exec this
iteration, web_search backend down): under Roll's efficient-market/bid-ask
bounce model, successive price changes exhibit negative serial covariance
whose magnitude reveals the effective bid-ask spread with NO order-book
data required:

    spread_t = 2 * sqrt(max(0, -Cov(delta_p_t, delta_p_{t-1})))

computed over a trailing rolling window of log-price changes (delta_p).
A rolling spread estimate is a rolling LIQUIDITY proxy: high estimated
spread => illiquid/bounce-dominated regime (wider effective transaction
costs, noisier price discovery); low estimated spread => liquid/efficient
regime. This is a genuinely new indicator family for this repo (0 prior
Roll/bid-ask-bounce entries) -- distinct from Corwin-Schultz (High-Low
range-based spread estimator, already tested in this repo) since Roll's
estimator uses only close-to-close serial covariance, not the H-L range.

This iteration reframes the liquidity signal as a CONTINUOUS SIZING dial
(the pattern that has rescued/extended most other single-purpose
oscillators in this repo's recent iterations) rather than a binary
liquidity-regime gate: inside an SMA(trend_window) uptrend, exposure scales
UP as estimated spread falls below its own rolling reference (calmer,
more liquid, more trustworthy trend), and DOWN toward zero as spread
estimates spike above reference (bid-ask-bounce dominated, noisy,
potentially adverse-selection-heavy regime) -- economically: don't lean
hard into a trend signal when the market's own price-formation process
looks unusually noisy/illiquid by this estimator.

Signal logic
------------
- Base directional signal: long-candidate when close > SMA(trend_window).
- delta_p = diff of log(close); Roll spread estimate over `roll_window`:
  cov1 = rolling covariance of delta_p_t and delta_p_{t-1} over roll_window;
  spread = 2*sqrt(max(0, -cov1)).
- spread_ref = rolling mean of spread over `ref_window` (self-referencing,
  no fixed constant threshold -- adapts to each symbol's own liquidity
  regime, equity vs crypto).
- inv_liquidity_ratio = spread_ref / (spread + tiny epsilon), clipped to
  [0, leverage_cap] -- exposure rises as current spread estimate falls
  below its own reference (more liquid than usual -> lean in), falls as
  spread estimate rises above reference (less liquid than usual -> back
  off). A deadband around ratio==1 avoids churn from estimator noise.
- Exposure while trend_long: the clipped inv_liquidity_ratio; 0 otherwise.

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


def _roll_spread(close: pd.Series, roll_window: int) -> pd.Series:
    """Rolling Roll's (1984) implied effective bid-ask spread estimate."""
    log_p = np.log(close.replace(0, np.nan))
    delta_p = log_p.diff()
    delta_p_lag = delta_p.shift(1)

    # Vectorized rolling covariance of delta_p_t vs delta_p_{t-1}:
    mean_dp = delta_p.rolling(roll_window).mean()
    mean_dp_lag = delta_p_lag.rolling(roll_window).mean()
    prod = (delta_p * delta_p_lag)
    mean_prod = prod.rolling(roll_window).mean()
    cov1 = mean_prod - mean_dp * mean_dp_lag

    spread = 2.0 * np.sqrt(np.maximum(0.0, -cov1))
    return spread


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    roll_window: int = 20,
    ref_window: int = 100,
    deadband: float = 0.15,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    spread = _roll_spread(close, roll_window)
    spread_ref = spread.rolling(ref_window).mean()

    epsilon = 1e-9
    ratio = spread_ref / (spread + epsilon)
    ratio = ratio.replace([np.inf, -np.inf], np.nan)

    # Deadband around ratio == 1.0 (spread estimate near its own reference):
    # treat as neutral base_exposure of 1.0 rather than amplifying noise.
    centered = ratio - 1.0
    dampened = np.where(centered.abs() <= deadband, 0.0, centered)
    raw_exposure = (1.0 + dampened).astype(float)

    exposure = pd.Series(raw_exposure, index=ratio.index).clip(
        lower=0.0, upper=leverage_cap
    ).fillna(0.0)

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
