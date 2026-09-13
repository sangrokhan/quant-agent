"""Strategy: SMA200 trend-following gate with rolling Downside Beta (vs SPY
benchmark) inverse-sizing overlay.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per Wikipedia (https://en.wikipedia.org/wiki/Downside_beta, browser_exec)
and Google SERP synthesis: Downside Beta (Hogan and Warren 1974; Bawa and
Lindenberg 1977; D-CAPM) = Cov(r_i, r_m | r_m < target) /
Var(r_m | r_m < target) -- i.e. an asset's beta computed ONLY on days the
benchmark's excess return is negative (target=0 here), capturing
sensitivity to MARKET DOWNSIDE specifically. This is distinct from the
repo's existing Treynor-Ratio strategy (2026-09-13 entry, rejected), which
uses an ordinary ALL-DAYS beta vs SPY as its risk denominator; this
iteration isolates the DOWNSIDE-ONLY beta as the risk measure instead,
testing whether restricting the beta estimation window to bad-market days
produces a more useful sizing signal than the ordinary CAPM beta did.
Exposure scales INVERSELY with trailing downside beta: lower sensitivity to
market crashes implies more exposure allowed. First Downside-Beta-based
strategy in this repo.

Signal logic
------------
- Base directional signal: long when close > SMA(trend_window), flat
  otherwise (identical trend gate to the repo's other sizing-overlay
  strategies for direct comparability).
- Benchmark = SPY daily log returns (loaded independently of the traded
  symbol, even when the traded symbol IS SPY or is crypto -- a falsification
  test for crypto, same pattern as the repo's existing Treynor entry).
- Within each trailing `beta_window`, restrict to days where the benchmark's
  daily log return < 0 (downside days only); downside_beta =
  Cov(asset_ret, bench_ret | bench_ret<0) / Var(bench_ret | bench_ret<0).
- Exposure: scale = clip(beta_reference / (downside_beta + adjustment), 0,
  leverage_cap). Applied only while the trend gate is long.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_benchmark_returns(index: pd.DatetimeIndex) -> pd.Series:
    """Load SPY daily log returns as the fixed market benchmark, aligned to
    ``index``. Cached at module level to avoid repeat network/cache hits
    across grid-test cells within one process."""
    global _BENCH_CACHE
    try:
        _BENCH_CACHE
    except NameError:
        _BENCH_CACHE = None

    if _BENCH_CACHE is None:
        import sys
        import os

        sys.path.insert(
            0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
        )
        from loaders import load_equity  # noqa: E402

        start = datetime(2015, 1, 1)
        end = datetime(2026, 12, 31)
        bench_df = _prep(load_equity("SPY", start, end))
        bench_ret = np.log(bench_df["close"] / bench_df["close"].shift(1))
        _BENCH_CACHE = bench_ret

    bench_ret = _BENCH_CACHE
    # Align to strategy index; both are tz-aware daily timestamps.
    return bench_ret.reindex(index)


def _rolling_downside_beta(
    asset_ret: pd.Series, bench_ret: pd.Series, window: int
) -> pd.Series:
    """Rolling downside beta: Cov(asset,bench | bench<0) / Var(bench | bench<0)."""
    a = asset_ret.to_numpy(dtype=float)
    b = bench_ret.to_numpy(dtype=float)
    n = len(a)
    out = np.full(n, np.nan)
    if n < window:
        return pd.Series(out, index=asset_ret.index)

    for end in range(window - 1, n):
        start = end - window + 1
        a_seg = a[start:end + 1]
        b_seg = b[start:end + 1]
        mask = (~np.isnan(a_seg)) & (~np.isnan(b_seg)) & (b_seg < 0)
        if mask.sum() < 10:
            continue
        a_down = a_seg[mask]
        b_down = b_seg[mask]
        var_b = float(np.var(b_down))
        if var_b <= 1e-12:
            continue
        cov_ab = float(np.mean((a_down - a_down.mean()) * (b_down - b_down.mean())))
        out[end] = cov_ab / var_b

    return pd.Series(out, index=asset_ret.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    beta_window: int = 90,
    adjustment: float = 0.1,
    beta_reference: float = 1.0,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    asset_ret = np.log(close / close.shift(1))
    bench_ret = _get_benchmark_returns(close.index)

    downside_beta = _rolling_downside_beta(asset_ret, bench_ret, beta_window)

    raw_exposure = (beta_reference / (downside_beta.abs() + adjustment)).astype(float)
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
