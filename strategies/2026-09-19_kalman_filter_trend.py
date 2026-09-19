"""Strategy: 1D Kalman-filter trend estimate, long/short direction of filtered slope.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-19-056):
Per Alphrex's "Kalman Filter Trend" strategy page
(https://alphrex.com/strategies/kalman), a 1D Kalman filter treats the true
latent log-price trend as a hidden state observed through noisy price
measurements: state x(t) = x(t-1) + w(t), w ~ N(0, process_noise); obs
z(t) = x(t) + v(t), v ~ N(0, obs_noise). The Kalman gain K(t) adaptively
weights how much the filter trusts new observations vs its prior
prediction -- unlike a fixed-window moving average, this weighting is
optimal in the least-squares sense (under the model's Gaussian
assumptions) and self-calibrates to the observed price series' own
noise/signal ratio at each Q/R setting. Alphrex's own disclosed default
parameters: process_noise (Q) = 0.0001, obs_noise (R) = 0.01. Trading
rule: go long when the filtered state's period-over-period change is
positive (trend estimate rising), short when negative. First
Kalman-filter-based strategy in this repo (zero prior Kalman entries in
strategies_index.jsonl) -- genuinely distinct smoothing/trend-estimation
mechanism from every other adaptive filter already tested (KAMA, FRAMA,
Ehlers-family filters, Hull MA) since it is a recursive Bayesian estimator
rather than a fixed-formula weighted average.

Signal logic
------------
- Apply the 1D Kalman filter to log(close) with (process_noise, obs_noise)
  as tunable parameters.
- trend_delta = diff(filtered_state).
- Long (position=1) when trend_delta > 0; short (position=-1) when
  trend_delta < 0; flat (0) only on the very first bar (no prior delta).
- This mirrors the source's own signal exactly (long/short, not the
  usual {0,1} contract in this repo -- consistent with how e.g. the
  copper/gold z-score hysteresis strategy also deviates from {0,1} when
  the source's own construction is inherently directional).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (-1/0/1 position)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def _kalman_filter(observations: np.ndarray, process_noise: float, obs_noise: float) -> np.ndarray:
    """1D Kalman filter (random-walk state model) over a log-price series."""
    n = len(observations)
    filtered = np.zeros(n, dtype=float)
    x_hat = observations[0]
    p = 1.0

    filtered[0] = x_hat
    for t in range(1, n):
        # Predict
        x_pred = x_hat
        p_pred = p + process_noise
        # Update
        k = p_pred / (p_pred + obs_noise)
        x_hat = x_pred + k * (observations[t] - x_pred)
        p = (1 - k) * p_pred
        filtered[t] = x_hat
    return filtered


def generate_signals(
    price_df: pd.DataFrame,
    process_noise: float = 0.0001,
    obs_noise: float = 0.01,
) -> pd.Series:
    """Return a {-1,0,1} long/short position series."""
    df = _prep(price_df)
    close = df["close"]

    log_prices = np.log(close.to_numpy(dtype=float))
    filtered = _kalman_filter(log_prices, process_noise, obs_noise)

    trend = np.diff(filtered, prepend=filtered[0])
    position = np.zeros(len(trend), dtype=int)
    position[trend > 0] = 1
    position[trend < 0] = -1
    position[0] = 0  # no prior delta on the first bar

    return pd.Series(position, index=close.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    process_noise: float = 0.0001,
    obs_noise: float = 0.01,
) -> pd.Series:
    """Return the strategy's daily return series."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(df, process_noise=process_noise, obs_noise=obs_noise)
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
