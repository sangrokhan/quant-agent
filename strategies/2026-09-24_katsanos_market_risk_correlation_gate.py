"""Strategy: SMA trend-following gated by Katsanos' "Market Risk" filter --
a rolling correlation-with-benchmark regime confirmation.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per Markos Katsanos' "A Low-Risk ETF Trading Strategy" (TASC October 2026
Traders' Tips, Python implementation by Rajeev Jain,
https://traders.com/Documentation/FEEDbk_docs/2026/10/TradersTips.html,
read this iteration via browser_exec after web_search's DuckDuckGo backend
failed with a TLS RequestError on the seed query). The source's disclosed
"cond_market_risk" filter is a genuinely new construction not yet tried in
this repo (prior RSMK/Katsanos entries -- 2026-09-12-153, 2026-09-16-171,
2026-09-18-137 -- all reused his RSMK relative-strength oscillator, never
this correlation-regime component):

    cond_market_risk = ((benchmark_roc > -6%) AND (corr(asset_ret, bm_ret) > CORMIN))
                     OR ((benchmark_roc < -6%) AND (corr(asset_ret, bm_ret) < -CORMIN))

i.e. it's "safe" to trade the asset's own trend when EITHER (a) the
benchmark is not in a meaningful drawdown and the asset is normally
POSITIVELY correlated with it (business-as-usual regime), OR (b) the
benchmark IS in a meaningful drawdown but the asset has flipped to
NEGATIVE correlation with it (a genuine diversifying/flight-to-quality
regime, not a false-safe illusion of decoupling). Katsanos' own rationale
(per the source article) is to avoid taking trend signals during regime
transitions where the asset's normal relationship with the broad market
has broken down in an ambiguous way (correlation near zero, or flipped
sign without following through into an actual defensive move).

This is adapted here as a REGIME GATE on a plain fast/slow SMA crossover
trend-following base strategy (rather than his ETF-rotation-specific
overextension logic), gated to a single-asset-vs-benchmark contract:
benchmark defaults to SPY for equity symbols, BTC/USDT for crypto symbols
(reusing this repo's established internal-benchmark-fetch pattern from
strategies/2026-09-16_rsmk_rsi_dual_recovery_gate.py and
strategies/2026-09-08_pairs_zscore_cointegration.py).

Signal logic
------------
- Trend signal: close crosses above fast SMA(fast_window) over slow
  SMA(slow_window) -> bullish; below -> bearish/flat.
- Benchmark ROC: benchmark_roc = pct_change(benchmark_close, roc_window).
- Rolling correlation: corr_window-day Pearson correlation of the asset's
  own daily returns vs the benchmark's daily returns.
- Market-risk gate (per Katsanos' disclosed cond_market_risk):
    (benchmark_roc > roc_threshold AND corr > cor_min) OR
    (benchmark_roc <= roc_threshold AND corr < -cor_min)
- Long entry: fast SMA > slow SMA AND market_risk gate is True.
- Exit: fast SMA crosses back below slow SMA, OR the market-risk gate
  flips False (risk-off exit), OR a max_hold_days safety time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position).
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


def _load_benchmark(index: pd.DatetimeIndex, asset_class: str, benchmark_symbol: str) -> pd.Series:
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity, load_crypto  # noqa: E402

    start = index.min()
    end = index.max() + timedelta(days=2)
    if asset_class == "crypto":
        bench_df = load_crypto(benchmark_symbol, start, end)
    else:
        bench_df = load_equity(benchmark_symbol, start, end)
    bench_df = _prep(bench_df)
    return bench_df["close"]


def _market_risk_gate(
    close: pd.Series,
    benchmark: pd.Series,
    roc_window: int,
    roc_threshold: float,
    corr_window: int,
    cor_min: float,
) -> pd.Series:
    bm = benchmark.reindex(close.index).ffill()
    bm_roc = bm.pct_change(roc_window) * 100.0

    asset_ret = close.pct_change()
    bm_ret = bm.pct_change()
    corr = asset_ret.rolling(corr_window).corr(bm_ret)

    gate = ((bm_roc > roc_threshold) & (corr > cor_min)) | (
        (bm_roc <= roc_threshold) & (corr < -cor_min)
    )
    return gate.fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    asset_class: str = "equity",
    benchmark_symbol: str = "SPY",
    fast_window: int = 20,
    slow_window: int = 60,
    roc_window: int = 6,
    roc_threshold: float = -6.0,
    corr_window: int = 100,
    cor_min: float = 0.5,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a 0/1 long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    benchmark = _load_benchmark(df.index, asset_class, benchmark_symbol)

    fast_sma = close.rolling(fast_window).mean()
    slow_sma = close.rolling(slow_window).mean()
    trend_up = (fast_sma > slow_sma).fillna(False)

    gate = _market_risk_gate(close, benchmark, roc_window, roc_threshold, corr_window, cor_min)

    entry_cond = trend_up & gate

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_days = 0
    for i in range(len(df)):
        if in_position:
            hold_days += 1
            if (not trend_up.iloc[i]) or (not gate.iloc[i]) or hold_days >= max_hold_days:
                in_position = False
                hold_days = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_cond.iloc[i]:
                in_position = True
                hold_days = 1
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    asset_class: str = "equity",
    benchmark_symbol: str = "SPY",
    fast_window: int = 20,
    slow_window: int = 60,
    roc_window: int = 6,
    roc_threshold: float = -6.0,
    corr_window: int = 100,
    cor_min: float = 0.5,
    max_hold_days: int = 60,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_returns = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        asset_class=asset_class,
        benchmark_symbol=benchmark_symbol,
        fast_window=fast_window,
        slow_window=slow_window,
        roc_window=roc_window,
        roc_threshold=roc_threshold,
        corr_window=corr_window,
        cor_min=cor_min,
        max_hold_days=max_hold_days,
    )
    strat_returns = daily_returns * position.shift(1).fillna(0)
    return strat_returns
