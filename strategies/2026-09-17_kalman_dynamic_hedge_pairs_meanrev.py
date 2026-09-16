"""Strategy: Kalman-filter dynamic-hedge-ratio pairs mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per QuantStart's "Dynamic Hedge Ratio Between ETF Pairs Using the Kalman
Filter" and multiple corroborating sources found via browser_exec Google
SERP fallback this iteration (LinkedIn/Dr. Heather Dempsey's Kalman-filter-
breaks-in-pairs-trading post, Robot Wealth's Kalman filter pairs trading
example, QuantT's Pairs Trading Complete Strategy Guide, Papers-With-
Backtest's Kalman Filter for Trading course), the standard state-space
formulation for a time-varying hedge ratio is:

    y_t = x_t * beta_t + v_t,          v_t ~ N(0, R)   (observation eq.)
    beta_t = beta_{t-1} + w_t,         w_t ~ N(0, Q)   (state/random-walk eq.)

A 1D Kalman filter recursively estimates beta_t (the time-varying hedge
ratio between two related log-prices) WITHOUT a fixed rolling-OLS window,
adapting continuously as the relationship between the two assets drifts --
this repo's existing pairs-trading strategies (JPM/BAC, CVX/XOM, GDX/RING,
SPY/QQQ, ETH/BTC, etc.) all use a rolling-OLS hedge ratio recomputed over a
fixed lookback window, a structurally different (and, per the sources
above, generally noisier/slower-to-adapt) estimator. This iteration is the
first Kalman-filter-based DYNAMIC HEDGE RATIO pairs strategy in this repo
(distinct from the already-tested single-asset Kalman trend-following/
mean-reversion variants at 2026-09-05-056/2026-09-08-052/2026-09-11-112,
none of which involve a second instrument or a hedge ratio at all).

Kalman filter recursion (scalar beta state, per QuantStart's pykalman-based
implementation, reimplemented here from scratch with numpy since pykalman
isn't a repo dependency):

    Predict:   beta_pred = beta_{t-1};  P_pred = P_{t-1} + Q
    Update:    e_t = y_t - x_t * beta_pred                  (innovation)
               S_t = x_t^2 * P_pred + R                       (innovation var)
               K_t = P_pred * x_t / S_t                        (Kalman gain)
               beta_t = beta_pred + K_t * e_t
               P_t = (1 - K_t * x_t) * P_pred

Signal logic
------------
- x_t = log(close of partner_symbol), y_t = log(close of price_df's own
  symbol). Kalman filter recursively estimates beta_t (no lookback window).
- spread_t = y_t - beta_t * x_t (the Kalman-filtered residual).
- z-score of spread_t over a trailing z_window (only the z-score windowing
  is fixed-lookback; the hedge ratio itself is fully adaptive).
- Entry (long the spread, i.e. conceptually long-A/short-B, expressed here
  as position=1 "hold A"): z <= -entry_z (A cheap relative to B per the
  Kalman-implied relationship).
- Exit: z reverts to >= -exit_z, or a max_hold_days time-stop.
- Flat otherwise.

Framework adaptation note: same partner-leg-fetch pattern as
strategies/2026-09-08_pairs_zscore_cointegration.py -- price_df carries the
"A" leg's OHLCV, and the "B" leg is fetched internally via data/loaders.py
keyed off price_df's own date range and the partner_symbol/asset_class
params, since validation/grid_test.py drives one symbol at a time.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_partner(index: pd.DatetimeIndex, asset_class: str, partner_symbol: str) -> pd.Series:
    """Fetch the partner leg's close series over price_df's date range."""
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity, load_crypto  # noqa: E402

    start = index.min()
    end = index.max() + timedelta(days=2)
    if asset_class == "crypto":
        partner_df = load_crypto(partner_symbol, start, end)
    else:
        partner_df = load_equity(partner_symbol, start, end)
    partner_df = _prep(partner_df)
    return partner_df["close"]


def _kalman_beta(y: np.ndarray, x: np.ndarray, q: float, r: float) -> np.ndarray:
    """Recursive scalar Kalman filter estimate of the time-varying hedge
    ratio beta_t in y_t = x_t*beta_t + v_t, beta_t = beta_{t-1} + w_t."""
    n = len(y)
    beta = np.zeros(n)
    p = 1.0  # initial state variance
    beta_est = 0.0
    for t in range(n):
        # Predict
        p_pred = p + q
        # Update
        xt = x[t]
        s = xt * xt * p_pred + r
        if s <= 0 or np.isnan(xt) or np.isnan(y[t]):
            beta[t] = beta_est
            p = p_pred
            continue
        k = p_pred * xt / s
        e = y[t] - xt * beta_est
        beta_est = beta_est + k * e
        p = (1.0 - k * xt) * p_pred
        beta[t] = beta_est
    return beta


def _spread_zscore(
    price_df: pd.DataFrame,
    asset_class: str,
    partner_symbol: str,
    q: float,
    r: float,
    z_window: int,
) -> pd.Series:
    df = _prep(price_df)
    close_a = df["close"]
    close_b = _load_partner(df.index, asset_class, partner_symbol)
    close_b = close_b.reindex(close_a.index).ffill()

    log_a = np.log(close_a.replace(0, np.nan)).values
    log_b = np.log(close_b.replace(0, np.nan)).values

    beta_t = _kalman_beta(log_a, log_b, q=q, r=r)
    spread = pd.Series(log_a - beta_t * log_b, index=close_a.index)

    spread_mean = spread.rolling(z_window).mean()
    spread_std = spread.rolling(z_window).std()
    z = (spread - spread_mean) / spread_std.replace(0, np.nan)
    return z


def generate_signals(
    price_df: pd.DataFrame,
    asset_class: str = "equity",
    partner_symbol: str = "QQQ",
    q: float = 1e-4,
    r: float = 1e-2,
    z_window: int = 20,
    entry_z: float = 2.0,
    exit_z: float = 0.5,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a 0/1 long/flat position series (long = long price_df's own
    symbol, conceptually short the partner leg)."""
    df = _prep(price_df)
    z = _spread_zscore(df, asset_class, partner_symbol, q, r, z_window)

    position = pd.Series(0.0, index=z.index)
    in_position = False
    entry_idx = -1
    for i in range(len(z)):
        zt = z.iloc[i]
        if np.isnan(zt):
            position.iloc[i] = 1.0 if in_position else 0.0
            continue
        if not in_position:
            if zt <= -entry_z:
                in_position = True
                entry_idx = i
        else:
            held = i - entry_idx
            if zt >= -exit_z or held >= max_hold_days:
                in_position = False
        position.iloc[i] = 1.0 if in_position else 0.0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs) on the
    price_df's own leg (A)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
