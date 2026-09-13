"""Strategy: SMA200 trend-following gate combined with a rolling Up/Down
Capture Ratio spread (vs SPY benchmark) regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per https://metricgate.com/docs/up-down-capture-ratio/ (browser_exec;
visited earlier this cron trigger, used for this iteration's hypothesis):
Up-Capture (UC) = 100 * R_p^up / R_b^up, Down-Capture (DC) =
100 * R_p^down / R_b^down, where R^up/R^down are geometric compounded
returns over periods when the benchmark rose/fell respectively. Capture
spread = UC - DC. This is a fundamentally different construction from
every ratio-based sizing overlay already tested in this repo (Sharpe/
Sortino/Omega/Downside-Beta/etc, all single-number risk-adjusted-return
ratios computed over the ENTIRE trailing window): capture ratios instead
SPLIT the window by benchmark sign and compare compounded participation
rates separately for up vs down periods, isolating asymmetric
benchmark-relative behavior (an asset that "keeps up in rallies while
cushioning drawdowns" has UC>100, DC<100, spread>0). This iteration uses
the rolling capture spread as a binary regime filter (trade only when
capture_spread > spread_threshold, i.e. only when the asset has recently
shown favorable upside/downside asymmetry vs SPY) layered on the same
SMA(200) trend gate used by the repo's other sizing-overlay strategies.
First Up/Down-Capture-Ratio-based strategy in this repo.

Signal logic
------------
- Base directional signal: long-candidate when close > SMA(trend_window).
- Benchmark = SPY daily simple returns (loaded independently of the traded
  symbol, even when the traded symbol IS SPY or is crypto -- a
  falsification test for crypto, same pattern as the repo's existing
  Treynor-Ratio and Downside-Beta entries).
- Within each trailing `capture_window`, split days into up-days
  (bench_ret > 0) and down-days (bench_ret < 0); compute compounded
  (geometric) returns for asset and benchmark over each subset; UC = 100 *
  asset_up_compound / bench_up_compound, DC = 100 * asset_down_compound /
  bench_down_compound; capture_spread = UC - DC.
- Regime gate: long only when trend_long AND capture_spread >
  spread_threshold; flat otherwise (fully binary allocation, no continuous
  scaling -- exposure is 0 or `leverage_cap`).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (values in
    {0, leverage_cap}).
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
    """Load SPY daily simple returns as the fixed market benchmark, aligned
    to ``index``. Cached at module level to avoid repeat network/cache hits
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
        bench_ret = bench_df["close"].pct_change()
        _BENCH_CACHE = bench_ret

    bench_ret = _BENCH_CACHE
    return bench_ret.reindex(index)


def _rolling_capture_spread(
    asset_ret: pd.Series, bench_ret: pd.Series, window: int
) -> pd.Series:
    """Rolling capture spread = UC - DC (percentage points)."""
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
        mask_valid = (~np.isnan(a_seg)) & (~np.isnan(b_seg))
        a_seg = a_seg[mask_valid]
        b_seg = b_seg[mask_valid]
        if len(a_seg) < 10:
            continue

        up_mask = b_seg > 0
        down_mask = b_seg < 0
        if up_mask.sum() < 3 or down_mask.sum() < 3:
            continue

        a_up_compound = np.prod(1.0 + a_seg[up_mask]) - 1.0
        b_up_compound = np.prod(1.0 + b_seg[up_mask]) - 1.0
        a_down_compound = np.prod(1.0 + a_seg[down_mask]) - 1.0
        b_down_compound = np.prod(1.0 + b_seg[down_mask]) - 1.0

        if abs(b_up_compound) < 1e-8 or abs(b_down_compound) < 1e-8:
            continue

        uc = 100.0 * a_up_compound / b_up_compound
        dc = 100.0 * a_down_compound / b_down_compound
        out[end] = uc - dc

    return pd.Series(out, index=asset_ret.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    capture_window: int = 90,
    spread_threshold: float = 0.0,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a binary {0, leverage_cap} exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    asset_ret = close.pct_change()
    bench_ret = _get_benchmark_returns(close.index)

    capture_spread = _rolling_capture_spread(asset_ret, bench_ret, capture_window)
    quality_ok = (capture_spread > spread_threshold).fillna(False)

    long_now = trend_long.fillna(False) & quality_ok
    position = pd.Series(
        np.where(long_now, leverage_cap, 0.0), index=close.index
    )
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
