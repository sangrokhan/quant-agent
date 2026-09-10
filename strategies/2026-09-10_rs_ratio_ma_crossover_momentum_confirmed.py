"""Strategy: Relative-Strength (RS) ratio-vs-smoothed-MA crossover, momentum-
confirmed, benchmark-relative timing.

Hypothesis
----------
Per https://wealthmanifestnow.com/using-relative-strength-to-time-sector-rotation/
(read via browser_exec this iteration; web_search DDGS backend failed 3x
this cron trigger with TLS connection errors): a Relative Strength (RS)
ratio (asset close / benchmark close) crossing above its own smoothed moving
average marks the start of a sustained outperformance phase; confirmed by RS
momentum (rate-of-change of the RS ratio) turning positive for >= 2
consecutive periods (acceleration, not a stall); and gated by the asset's
own absolute price being above its own moving average (avoid buying relative
strength while the asset itself is in an absolute downtrend). Exit when the
RS ratio crosses back below its smoothed MA, OR RS momentum turns negative
for >= 2 consecutive periods, OR a volatility-based stop (a fixed pct below
entry) triggers.

This is mechanically distinct from this repo's already-tested/accepted "IBD
Relative Strength Line breakout confirmation" (id=2026-09-09-039), which uses
a PRICE breakout (new N-day high) as the primary trigger and merely requires
the RS line to ALSO be near its own high as a confirmation filter. Here the
RS-line crossover of its own smoothed MA IS the primary entry trigger (not a
confirmation of a separate price signal), with an added RS-momentum
persistence filter and a fixed-pct stop-loss backstop that 039 lacks.

Tested single-asset vs a fixed benchmark: QQQ/SPY vs SPY/QQQ cross-benchmark
(equity) and BTC/USDT vs ETH/USDT (crypto), per data/loaders.py's
single-symbol OHLCV interface -- the benchmark series is loaded and joined
by date the same way this repo's existing pairs-trade/cross-asset strategies
do it.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)

NOTE: since generate_signals/generate_returns must accept a single
price_df per the grid-test harness's calling convention, the benchmark
series is fetched internally via data/loaders.py using a `benchmark_symbol`
kwarg and `asset_class` kwarg (defaults chosen so equity uses SPY as
benchmark and crypto uses BTC/USDT).
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_benchmark(price_df: pd.DataFrame, benchmark_symbol: str, asset_class: str) -> pd.Series:
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    from data.loaders import load_equity, load_crypto

    df = _prep(price_df)
    start = df.index.min()
    end = df.index.max()
    # pad a bit to make sure we have coverage after alignment
    start_dt = start.to_pydatetime() if hasattr(start, "to_pydatetime") else start
    end_dt = end.to_pydatetime() if hasattr(end, "to_pydatetime") else end

    if asset_class == "crypto":
        bench_df = load_crypto(benchmark_symbol, start_dt, end_dt)
    else:
        bench_df = load_equity(benchmark_symbol, start_dt, end_dt)

    bench_df = _prep(bench_df)
    return bench_df["close"]


def _compute_rs_signal(
    df: pd.DataFrame,
    benchmark_close: pd.Series,
    rs_ma_window: int,
    rs_mom_window: int,
    price_trend_window: int,
):
    close = df["close"]
    bench_aligned = benchmark_close.reindex(close.index).ffill()

    rs_ratio = close / bench_aligned
    rs_ma = rs_ratio.rolling(rs_ma_window).mean()
    rs_momentum = rs_ratio.pct_change(rs_mom_window)

    price_ma = close.rolling(price_trend_window).mean()
    price_uptrend = close > price_ma

    return rs_ratio, rs_ma, rs_momentum, price_uptrend


def generate_signals(
    price_df: pd.DataFrame,
    rs_ma_window: int = 20,
    rs_mom_window: int = 10,
    price_trend_window: int = 50,
    stop_pct: float = 0.07,
    max_hold_days: int = 60,
    benchmark_symbol: str = "SPY",
    asset_class: str = "equity",
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    benchmark_close = _load_benchmark(price_df, benchmark_symbol, asset_class)
    rs_ratio, rs_ma, rs_momentum, price_uptrend = _compute_rs_signal(
        df, benchmark_close, rs_ma_window, rs_mom_window, price_trend_window
    )

    rs_above_ma = rs_ratio > rs_ma
    rs_cross_up = rs_above_ma & ~rs_above_ma.shift(1).fillna(False)
    rs_mom_pos_streak = (rs_momentum > 0).rolling(2).sum() >= 2
    rs_mom_neg_streak = (rs_momentum < 0).rolling(2).sum() >= 2

    entry_signal = rs_cross_up & rs_mom_pos_streak.shift(0).fillna(False) & price_uptrend.fillna(False)
    exit_rs_cross_down = ~rs_above_ma
    exit_rs_mom_neg = rs_mom_neg_streak

    idx_list = close.index
    n = len(idx_list)
    position = pd.Series(0, index=idx_list, dtype=int)

    in_pos = False
    entry_idx = -1
    entry_price = None

    entry_vals = entry_signal.fillna(False).values
    exit_cross_vals = exit_rs_cross_down.fillna(True).values
    exit_mom_vals = exit_rs_mom_neg.fillna(False).values
    close_vals = close.values

    for i in range(n):
        if not in_pos:
            if entry_vals[i]:
                in_pos = True
                entry_idx = i
                entry_price = close_vals[i]
                position.iloc[i] = 1
        else:
            held_days = i - entry_idx
            stop_hit = close_vals[i] <= entry_price * (1.0 - stop_pct)
            exit_signal = exit_cross_vals[i] or exit_mom_vals[i] or stop_hit or held_days >= max_hold_days
            if exit_signal:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1

    return position.fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    rs_ma_window: int = 20,
    rs_mom_window: int = 10,
    price_trend_window: int = 50,
    stop_pct: float = 0.07,
    max_hold_days: int = 60,
    benchmark_symbol: str = "SPY",
    asset_class: str = "equity",
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        rs_ma_window=rs_ma_window,
        rs_mom_window=rs_mom_window,
        price_trend_window=price_trend_window,
        stop_pct=stop_pct,
        max_hold_days=max_hold_days,
        benchmark_symbol=benchmark_symbol,
        asset_class=asset_class,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = daily_returns * position.shift(1).fillna(0)
    return strat_returns
