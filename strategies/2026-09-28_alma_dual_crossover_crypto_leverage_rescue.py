"""Strategy: ALMA Dual Crossover, CRYPTO LEVERAGE-CAP RESCUE (follow-up for
near-miss 2026-09-28-050).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-28-050):
The plain ALMA dual-crossover (strategies/2026-09-28_alma_dual_crossover_trend.py,
fast_window=14/slow_window=34) passed Sharpe, transaction-cost-survival,
walk-forward, and parameter-sensitivity on BOTH BTC/USDT (Sharpe 1.083) and
ETH/USDT (Sharpe 1.085), but decisively failed max-drawdown (0.584 and
0.537 respectively vs the 0.25 cap) -- a full-exposure (leverage=1.0)
trend-following crossover simply whipsaws too hard through crypto's higher
realized volatility. This repo has an established, previously-successful
rescue pattern for exactly this failure mode (Sharpe/TC/WF/param-sensitivity
all pass, MDD alone fails): scale position size down by a fixed
`leverage_cap` multiplier and re-check whether MDD clears the 0.25 threshold
while Sharpe (leverage-invariant for pure long/flat exposure with no vol
targeting) stays above 1.0. Prior successful applications of this exact
pattern: Break of Structure BTC/USDT (2026-09-24-041, leverage_cap=0.7),
Elder-Ray, Chaikin Oscillator, Twiggs Money Flow, Ultimate Oscillator (all
referenced in this repo's knowledge base).

No new external source consulted this iteration -- internal parameter
rescue of this same cron trigger's own near-miss, per RESEARCH_LOOP.md
Step 3's guidance to prefer revisiting flagged near-misses.

Signal logic: IDENTICAL to the parent strategy (ALMA(fast_window) crosses
above ALMA(slow_window) -> long; crosses below -> exit; max_hold_days
time-stop), except position size is `leverage_cap` (a fraction <= 1.0)
instead of a full 1.0 while in a trade.

Interface contract for validators (see validation/validators.py) and
validation/grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  (position series with
        values in {0, leverage_cap} instead of strictly {0,1})
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _alma(series: pd.Series, window: int, offset: float = 0.85, sigma: float = 6.0) -> pd.Series:
    """Arnaud Legoux Moving Average, causal (no look-ahead)."""
    if window < 1:
        raise ValueError("window must be >= 1")
    m = math.floor(offset * (window - 1))
    s = window / sigma
    idx = np.arange(window)
    weights = np.exp(-((idx - m) ** 2) / (2 * s * s))
    weights = weights / weights.sum()

    values = series.to_numpy(dtype=float)
    n = len(values)
    out = np.full(n, np.nan)
    for t in range(window - 1, n):
        window_slice = values[t - window + 1 : t + 1]
        if np.any(np.isnan(window_slice)):
            continue
        out[t] = float(np.dot(window_slice, weights))
    return pd.Series(out, index=series.index)


def generate_signals(
    price_df: pd.DataFrame,
    fast_window: int = 14,
    slow_window: int = 34,
    offset: float = 0.85,
    sigma: float = 6.0,
    max_hold_days: int = 60,
    leverage_cap: float = 0.4,
) -> pd.Series:
    """Return a {0, leverage_cap} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fast_alma = _alma(close, fast_window, offset=offset, sigma=sigma)
    slow_alma = _alma(close, slow_window, offset=offset, sigma=sigma)

    cross_up = (fast_alma > slow_alma) & (fast_alma.shift(1) <= slow_alma.shift(1))
    cross_down = (fast_alma < slow_alma) & (fast_alma.shift(1) >= slow_alma.shift(1))

    cross_up = cross_up.fillna(False)
    cross_down = cross_down.fillna(False)

    position = pd.Series(0.0, index=close.index, dtype=float)
    in_position = False
    entry_idx = 0
    n = len(close)

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(cross_down.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0.0
                continue
            position.iloc[i] = leverage_cap
        else:
            if bool(cross_up.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = leverage_cap
            else:
                position.iloc[i] = 0.0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
