"""Strategy: SMA200 trend-following gate with rolling Ulcer Performance
Index (Martin Ratio) dynamic exposure scaling.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per https://en.wikipedia.org/wiki/Ulcer_index (Peter Martin, 1987, read via
browser_exec): the Ulcer Performance Index (UPI, a.k.a. Martin Ratio) =
(return - risk_free_rate) / Ulcer Index, where Ulcer Index is the
QUADRATIC MEAN (root-mean-square, i.e. divided by N, unlike the already-
tested Burke Ratio's root-SUM-of-squares with no /N averaging) of per-bar
retracement from the running peak. Distinct from Burke Ratio
(2026-09-13-052, no /N normalization -> grows with window length/sample
count) and Pain Ratio (2026-09-13-051, arithmetic MEAN of retracement, not
RMS -> weights shallow-but-frequent drawdowns differently than a squared
measure). This repo has previously only used the Ulcer Index as a binary
entry-filter THRESHOLD (2026-09-04-144, 2026-09-10-045), never as a
continuous dynamic-exposure sizing overlay -- this iteration closes that
gap. Scales an SMA(200) trend gate's exposure by the trailing Ulcer
Performance Index. First UPI/Martin-Ratio-based sizing strategy in this
repo.

Signal logic
------------
- Base directional signal: long when close > SMA(trend_window), flat
  otherwise (identical trend gate to the repo's other sizing-overlay
  strategies, for direct comparability).
- Within each trailing `ulcer_window`, compute the running-peak retracement
  R(t) = 100 * (price(t) - running_peak(t)) / running_peak(t) (<=0), then
  Ulcer Index = sqrt(mean(R(t)^2)) over the window.
- Annualized return over the same window (mean daily log return * 252).
- UPI = annualized_return / (ulcer_index + ulcer_adjustment), guarded
  against a near-zero denominator.
- Exposure: scale = clip(upi / upi_reference, 0, leverage_cap). Applied
  only while the trend gate is long.

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


def _rolling_upi(
    close: pd.Series, window: int, ulcer_adjustment: float
) -> pd.Series:
    """Rolling Ulcer Performance Index (Martin Ratio): annualized mean
    daily log return / (Ulcer Index + adjustment), where Ulcer Index is
    the RMS of per-bar running-peak retracement (percent) within the
    window."""
    values = close.to_numpy(dtype=float)
    n = len(values)
    out = np.full(n, np.nan)
    if n < window:
        return pd.Series(out, index=close.index)

    log_ret = np.log(close / close.shift(1)).to_numpy(dtype=float)

    for end in range(window - 1, n):
        start = end - window + 1
        seg = values[start:end + 1]
        running_peak = np.maximum.accumulate(seg)
        retracement_pct = 100.0 * (seg - running_peak) / running_peak  # <= 0
        ulcer_index = float(np.sqrt(np.mean(retracement_pct ** 2)))

        ret_seg = log_ret[start:end + 1]
        mean_daily_ret = np.nanmean(ret_seg)
        annualized_ret = mean_daily_ret * 252.0 * 100.0  # percent, matches Ulcer's percent scale

        denom = ulcer_index + ulcer_adjustment
        out[end] = annualized_ret / denom if denom > 1e-6 else np.nan

    return pd.Series(out, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    ulcer_window: int = 90,
    ulcer_adjustment: float = 0.5,
    upi_reference: float = 1.0,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    upi = _rolling_upi(close, ulcer_window, ulcer_adjustment)

    raw_exposure = (upi / upi_reference).astype(float)
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
