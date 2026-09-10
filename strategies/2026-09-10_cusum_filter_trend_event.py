"""Strategy: Symmetric CUSUM (Cumulative Sum) filter trend-event entry.

Hypothesis (see knowledge_base/strategies_log.jsonl for this run's id):
Per https://github.com/muMAJJI/Trading---CUSUM-FILTER (README describing the
symmetric CUSUM filter popularized by Lopez de Prado's "Advances in
Financial Machine Learning"): track two running cumulative sums of daily
log-returns, S+ (only accumulates positive deviations, resets to 0 on any
new negative excursion below 0) and S- (mirror, only accumulates negative
deviations). A "trend event" fires when S+ crosses above a threshold h
(persistent upward drift, not just one big daily move) or S- crosses below
-h (persistent downward drift). The source's own stated rationale: this
filters out one-off noisy price spikes that a naive moving-average
crossover would react to, since only a *sustained* run of same-direction
returns can build up enough cumulative sum to cross the threshold.

Adapted here as a single-asset long-only trend-following entry: long when
a positive CUSUM event fires (S+ >= h) while price is above its own
long-term trend filter (close > SMA(trend_window), standard regime gate
used throughout this repo); exit when a negative CUSUM event fires
(S- <= -h) or a max_hold_days time-stop. Threshold h is set as
h_mult * rolling realized volatility of daily log-returns (adaptive
threshold, since a fixed absolute h wouldn't generalize across QQQ/SPY/BTC/
ETH's very different volatility regimes).

First CUSUM-filter-family strategy in this repo -- distinct from
Ehlers-cycle/statistical-regime-detection entries already tested (Hurst
exponent regime, variance ratio, autocorrelation regime, HMM regime
switching) since those classify an ongoing state, while CUSUM specifically
flags discrete THRESHOLD-CROSSING EVENTS of accumulated directional drift.

Signal logic
------------
- log_ret = log(close / close.shift(1))
- vol = rolling std of log_ret over vol_window (adaptive threshold basis)
- h = h_mult * vol (per-bar adaptive threshold)
- S+_t = max(0, S+_{t-1} + log_ret_t); reset S+ to 0 immediately after it
  fires (crosses >= h_t) so each event is a fresh accumulation, not a
  runaway series.
- S-_t = min(0, S-_{t-1} + log_ret_t); mirror reset after firing.
- Entry (long): S+ fires (S+_t >= h_t) AND close > SMA(trend_window).
- Exit: S- fires (S-_t <= -h_t), OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _cusum_events(log_ret: pd.Series, h: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Symmetric CUSUM filter. Returns (pos_event, neg_event) boolean series.

    pos_event[t] True means S+ crossed >= h[t] at bar t (and S+ was reset to 0).
    neg_event[t] True means S- crossed <= -h[t] at bar t (and S- was reset to 0).
    """
    n = len(log_ret)
    values = log_ret.to_numpy()
    h_vals = h.to_numpy()

    s_pos = 0.0
    s_neg = 0.0
    pos_event = np.zeros(n, dtype=bool)
    neg_event = np.zeros(n, dtype=bool)

    for i in range(n):
        r = values[i]
        threshold = h_vals[i]
        if np.isnan(r) or np.isnan(threshold):
            continue

        s_pos = max(0.0, s_pos + r)
        s_neg = min(0.0, s_neg + r)

        if s_pos >= threshold:
            pos_event[i] = True
            s_pos = 0.0
        if s_neg <= -threshold:
            neg_event[i] = True
            s_neg = 0.0

    return (
        pd.Series(pos_event, index=log_ret.index),
        pd.Series(neg_event, index=log_ret.index),
    )


def generate_signals(
    price_df: pd.DataFrame,
    vol_window: int = 20,
    h_mult: float = 4.0,
    trend_window: int = 200,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    log_ret = np.log(close / close.shift(1))
    vol = log_ret.rolling(vol_window).std()
    h = h_mult * vol

    pos_event, neg_event = _cusum_events(log_ret, h)
    sma = close.rolling(trend_window).mean()

    entry_signal = pos_event & (close > sma)
    exit_signal = neg_event

    valid = sma.notna() & vol.notna()

    n = len(df.index)
    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if not valid.iloc[i]:
            position.iloc[i] = 0
            continue

        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(int) * daily_ret
    strat_returns.name = "strategy_returns"
    return strat_returns
