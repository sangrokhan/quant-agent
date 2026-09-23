"""Strategy: RSI(2) oversold mean-reversion (Larry Connors), gated by Katsanos'
"Market Risk" correlation-with-benchmark regime filter (same gate mechanism
validated this cron trigger on an SMA trend-following base in
strategies/2026-09-24_katsanos_market_risk_correlation_gate.py, now applied
to a mean-reversion base instead).

Hypothesis (knowledge_base id TBD, this cron trigger):
This repo's accepted RSI(2)/SMA(200) mean-reversion baseline (2026-09-03-005)
trades unconditionally whenever RSI(2) is oversold in a long-term uptrend.
Per Markos Katsanos' "A Low-Risk ETF Trading Strategy" (TASC October 2026
Traders' Tips, https://traders.com/Documentation/FEEDbk_docs/2026/10/TradersTips.html,
re-read this iteration), his disclosed cond_market_risk filter -- a rolling
correlation-with-benchmark regime confirmation -- was validated earlier this
cron trigger as a genuinely new gate mechanism on an SMA trend-following base
(id 2026-09-24-007, accepted QQQ+SPY). This iteration tests the SAME gate
mechanism on a DIFFERENT base strategy family (RSI(2) oversold mean-reversion
instead of SMA trend-following), to see whether the correlation-regime
confirmation generalizes as a filter across strategy TYPES, not just within
one. Prior repo entries used correlation-regime gates only with
z-score/pairs-trading mean-reversion (2026-09-20-047, rejected) or ETF-basket
momentum (2026-09-08-152); this is the first application of Katsanos' EXACT
two-branch construction (benchmark-drawdown-aware sign flip) to an RSI(2)
oversold-bounce entry.

Signal logic
------------
- RSI(2) < rsi_oversold AND close > SMA(sma_trend_window) (base Connors
  RSI(2) setup, per this repo's already-accepted 2026-09-03-005).
- Market-risk gate (Katsanos): (benchmark_roc(roc_window) > roc_threshold
  AND rolling_corr(asset_ret, bm_ret, corr_window) > cor_min) OR
  (benchmark_roc <= roc_threshold AND corr < -cor_min).
- Long entry: RSI(2) oversold AND trend filter AND market-risk gate all True.
- Exit: close crosses back above SMA(exit_sma_window), OR the market-risk
  gate flips False, OR a max_hold_days safety time-stop.

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


def _rsi(close: pd.Series, length: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - 100.0 / (1.0 + rs)
    return rsi.fillna(50.0)


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
    rsi_length: int = 2,
    rsi_oversold: float = 10.0,
    sma_trend_window: int = 200,
    exit_sma_window: int = 5,
    roc_window: int = 6,
    roc_threshold: float = -6.0,
    corr_window: int = 100,
    cor_min: float = 0.5,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a 0/1 long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    benchmark = _load_benchmark(df.index, asset_class, benchmark_symbol)

    rsi = _rsi(close, rsi_length)
    sma_trend = close.rolling(sma_trend_window).mean()
    exit_sma = close.rolling(exit_sma_window).mean()

    gate = _market_risk_gate(close, benchmark, roc_window, roc_threshold, corr_window, cor_min)

    entry_cond = (
        (rsi < rsi_oversold) & (close > sma_trend) & gate
    ).fillna(False)
    exit_meanrev = (close > exit_sma).fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_days = 0
    for i in range(len(df)):
        if in_position:
            hold_days += 1
            if exit_meanrev.iloc[i] or (not gate.iloc[i]) or hold_days >= max_hold_days:
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
    rsi_length: int = 2,
    rsi_oversold: float = 10.0,
    sma_trend_window: int = 200,
    exit_sma_window: int = 5,
    roc_window: int = 6,
    roc_threshold: float = -6.0,
    corr_window: int = 100,
    cor_min: float = 0.5,
    max_hold_days: int = 10,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_returns = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        asset_class=asset_class,
        benchmark_symbol=benchmark_symbol,
        rsi_length=rsi_length,
        rsi_oversold=rsi_oversold,
        sma_trend_window=sma_trend_window,
        exit_sma_window=exit_sma_window,
        roc_window=roc_window,
        roc_threshold=roc_threshold,
        corr_window=corr_window,
        cor_min=cor_min,
        max_hold_days=max_hold_days,
    )
    strat_returns = daily_returns * position.shift(1).fillna(0)
    return strat_returns
