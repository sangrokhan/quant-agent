"""Strategy: Abdi-Ranaldo close-vs-midrange spread-widening as a DIRECT
mean-reversion trigger (long-only), distinct mechanism from this repo's
Corwin-Schultz liquidity TREND-FILTER strategy.

Hypothesis (see knowledge_base/strategies_log.jsonl, this entry's id):
Per Abdi & Ranaldo (2017, Review of Financial Studies) "A Simple Estimation
of Bid-Ask Spreads from Daily Close, High, and Low Prices" -- read via
metricgate.com's worked methodology page
(https://metricgate.com/docs/abdi-ranaldo-spread-estimator/, plus
conceptual background from
https://quantmemo.com/concepts/abdi-ranaldo-spread-estimator, after
web_search's DDGS backend TLS-erroring on the initial formula query) -- the
estimator recovers an effective bid-ask spread from the cross-product of
the close's deviation from the day's log mid-range (eta_t=(H_t+L_t)/2) on
consecutive days: S^2 = 4*E[(c_t-eta_t)*(c_t-eta_{t+1})], truncated at
zero and square-rooted.

Distinct mechanism from this repo's already-accepted Corwin-Schultz
liquidity-regime TREND FILTER (2026-09-20-154, which uses the CS spread to
GATE an independent SMA trend signal): this strategy uses a transient
SPIKE in the rolling Abdi-Ranaldo spread estimate itself as a DIRECT
contrarian mean-reversion TRIGGER -- a sudden widening of the close-vs-
midrange cross-product often coincides with a sharp one-day price
dislocation (the close snapping far from the day's own high-low midpoint),
which this strategy treats as an overreaction worth fading, similar in
spirit to other single-day dislocation/gap-fade constructions already in
this repo but using a genuinely different (microstructure spread-based)
trigger statistic rather than a raw return/gap-size threshold. First
Abdi-Ranaldo-based strategy in this repo (0 prior "abdi ranaldo" hits).

Signal logic
------------
- Rolling Abdi-Ranaldo spread estimate S_t: for each rolling window of
  `ar_window` days, compute eta = (log(high)+log(low))/2, c = log(close),
  cross-product = (c_t - eta_t) * (c_t - eta_{t+1}) averaged over the
  window, S_t^2 = 4 * mean(cross-product) truncated at zero, S_t =
  sqrt(S_t^2). Assigned to the LAST day of each rolling window.
- Rolling percentile: S_t's own trailing `spread_pctile_window`-day
  percentile rank.
- Entry (long): S_t's percentile rank exceeds `spike_pctile_threshold`
  (spread-widening spike, i.e. dislocation) AND the day's own close < prior
  close (the dislocation was to the downside -- fade it by buying).
- Exit: `hold_days` fixed holding period after entry (short mean-reversion
  trade, no trend/regime exit condition -- this is intentionally a pure
  event-driven fade, not a regime-gated trend strategy), or immediately
  if already flat.

Interface contract (see validation/validators.py, validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _abdi_ranaldo_spread(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    """Rolling Abdi-Ranaldo (2017) effective spread estimate."""
    c = np.log(close)
    eta = (np.log(high) + np.log(low)) / 2.0

    c_t = c.iloc[:-1] if False else c  # keep full length; use shift for eta_{t+1}
    eta_next = eta.shift(-1)
    cross_term = (c - eta) * (c - eta_next)

    n = len(close)
    out = np.full(n, np.nan)
    vals = cross_term.values
    for end in range(window, n):
        w = vals[end - window : end]
        w = w[~np.isnan(w)]
        if len(w) < window // 2:
            out[end] = np.nan
            continue
        s2 = 4.0 * np.mean(w)
        out[end] = np.sqrt(max(s2, 0.0))
    return pd.Series(out, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    ar_window: int = 20,
    spread_pctile_window: int = 120,
    spike_pctile_threshold: float = 0.85,
    hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    spread = _abdi_ranaldo_spread(high, low, close, ar_window)
    spread_pctile = spread.rolling(spread_pctile_window).apply(
        lambda w: pd.Series(w).rank(pct=True).iloc[-1] if len(w) > 1 else np.nan,
        raw=False,
    )

    down_day = close < close.shift(1)
    spike = spread_pctile > spike_pctile_threshold
    entry = spike & down_day

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_arr = entry.fillna(False).values
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if held >= hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_arr[i]):
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
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
