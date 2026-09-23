"""Strategy: Rogers-Satchell / Parkinson volatility-ratio trend-vs-chop
regime gate on an SMA crossover trend-following signal.

Hypothesis (knowledge_base id 2026-09-24-004):
Per https://www.luxalgo.com/library/concept/rogers-satchell-estimator/, the
Rogers-Satchell (RS) volatility estimator is drift-independent (unbiased
when price trends), unlike the Parkinson estimator (which assumes zero
mean return and is inflated by directional drift). The source explicitly
states: "the spread between Rogers-Satchell and Parkinson ... over one
window decomposes measured volatility into wiggle versus one-way drift, a
regime read in itself." Concretely:

    RS_t  = ln(H/C)*ln(H/O) + ln(L/C)*ln(L/O)         (drift-independent)
    PK_t  = (1/(4*ln2)) * (ln(H/L))^2                  (assumes zero drift)

When price is trending strongly (one-way drift), RS stays a truer read of
the "wiggle" while Parkinson's zero-drift assumption causes it to
overstate volatility relative to RS less than in a choppy/range-bound
regime -- i.e. a LOW RS/Parkinson ratio indicates the bar's range is mostly
explained by directional travel (trend-dominated), while a HIGH ratio
indicates two-sided noise (chop-dominated). This strategy uses the rolling
RS/Parkinson ratio as a regime GATE: only take a classic SMA
fast/slow-crossover trend-following signal when the market is in the
trend-dominated (low ratio) regime, staying flat during chop-dominated
(high ratio) regimes where trend-following signals tend to whipsaw. First
Rogers-Satchell strategy in this repo (0 prior KB hits) -- distinct from
the same cron trigger's raw single-estimator Garman-Klass compression
breakout (2026-09-24-003) since this uses a two-estimator RATIO as a
regime classifier gating an entirely separate trend signal, not a
single-estimator percentile-breakout entry rule.

Signal logic
------------
- Compute RS_t and Parkinson_t per bar; smooth each with a rolling mean
  over vol_window days; take the ratio rs_pk_ratio = RS_smoothed /
  PK_smoothed (clipped away from zero-division).
- trend_regime = rs_pk_ratio <= regime_threshold (low ratio -> trending).
- Classic trend signal: fast SMA(fast_window) crosses above slow
  SMA(slow_window) -> bullish; below -> bearish.
- Long entry: bullish crossover state AND trend_regime is True.
- Exit: bearish crossover, OR trend_regime flips to False (chop), OR a
  max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
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


def _rogers_satchell(df: pd.DataFrame) -> pd.Series:
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    open_ = df["open"] if "open" in df.columns else df["close"]
    close = df["close"]

    def _safe_log_ratio(a, b):
        r = (a / b).replace([np.inf, -np.inf], np.nan).clip(lower=1e-8)
        return np.log(r)

    rs = (
        _safe_log_ratio(high, close) * _safe_log_ratio(high, open_)
        + _safe_log_ratio(low, close) * _safe_log_ratio(low, open_)
    )
    return rs.clip(lower=0.0)


def _parkinson(df: pd.DataFrame) -> pd.Series:
    high = df["high"] if "high" in df.columns else df["close"]
    low = df["low"] if "low" in df.columns else df["close"]
    log_hl = np.log((high / low).replace([np.inf, -np.inf], np.nan).clip(lower=1e-8))
    return (1.0 / (4.0 * np.log(2.0))) * (log_hl ** 2)


def generate_signals(
    price_df: pd.DataFrame,
    vol_window: int = 20,
    regime_threshold: float = 0.6,
    fast_window: int = 20,
    slow_window: int = 50,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    rs = _rogers_satchell(df)
    pk = _parkinson(df)
    rs_smoothed = rs.rolling(vol_window).mean()
    pk_smoothed = pk.rolling(vol_window).mean().replace(0.0, np.nan)
    ratio = (rs_smoothed / pk_smoothed).clip(lower=0.0, upper=10.0)

    trend_regime = (ratio <= regime_threshold).fillna(False).to_numpy()

    fast_sma = close.rolling(fast_window).mean()
    slow_sma = close.rolling(slow_window).mean()
    bullish = (fast_sma > slow_sma).fillna(False).to_numpy()
    bearish = (fast_sma <= slow_sma).fillna(False).to_numpy()

    pos_arr = [0] * n
    in_pos = False
    hold_days = 0

    for i in range(n):
        if in_pos:
            hold_days += 1
            if bearish[i] or (not trend_regime[i]) or hold_days >= max_hold_days:
                in_pos = False
                hold_days = 0
        else:
            if bullish[i] and trend_regime[i]:
                in_pos = True
                hold_days = 0
        pos_arr[i] = 1 if in_pos else 0

    return pd.Series(pos_arr, index=close.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    vol_window: int = 20,
    regime_threshold: float = 0.6,
    fast_window: int = 20,
    slow_window: int = 50,
    max_hold_days: int = 20,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        vol_window=vol_window,
        regime_threshold=regime_threshold,
        fast_window=fast_window,
        slow_window=slow_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strat_ret
