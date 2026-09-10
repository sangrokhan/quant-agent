"""Strategy: Relative Rotation Graph (RRG) JdK RS-Ratio / RS-Momentum leading
quadrant entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-109):
Per Julius de Kempenaer's Relative Rotation Graph (RRG) framework (per
StockCharts ChartSchool https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/rrg-relative-strength
and the exact double-smoothed WMA-ratio JdK RS-Ratio / percentage-based
RS-Momentum formula disclosed at
https://gist.github.com/tuhuynh27/c8abcf7f8469b7d91adac9a6947db64d):
a security's relative strength vs a benchmark, and the momentum of that
relative strength, together define four rotation-cycle quadrants (Lagging ->
Improving -> Leading -> Weakening -> Lagging, typically rotating clockwise).
Per StockCharts's own trading guidance and multiple secondary sources
(sharpely.io, Strike Money), the highest-conviction entry is the transition
from Improving into Leading (RS-Ratio crosses above 100 while RS-Momentum is
already >100, i.e. the security is now both outperforming the benchmark AND
that outperformance is accelerating). The corresponding exit is the
Leading->Weakening->Lagging transition, i.e. RS-Ratio crossing back below
100.

This repo's loaders provide single-symbol OHLCV, not a broad sector
universe, so this is adapted as a genuine two-asset RELATIVE strategy
(distinct from every prior single-asset absolute-momentum/trend strategy in
this repo): trade `symbol` long only while it is in the RRG Leading quadrant
relative to `benchmark_symbol` (RS-Ratio>100 AND RS-Momentum>100), i.e. only
while `symbol` is both outperforming the benchmark and accelerating that
outperformance. For crypto this pairs ETH (symbol) against BTC (benchmark)
per the standard altcoin-vs-BTC rotation framing; for equity this pairs QQQ
(symbol) against SPY (benchmark).

Formula (from the gist, itself a standard/public restatement of JdK's
published RRG mechanics):
    RS = (security_price / benchmark_price) * 100
    RS_smooth = WMA(RS, wma_window)
    RS_benchmark_smooth = WMA(RS_smooth, wma_window)
    RS_Ratio = (RS_smooth / RS_benchmark_smooth) * 100
    RS_Momentum = (RS_Ratio / RS_Ratio.shift(momentum_period)) * 100

Signal logic
------------
- Entry (long `symbol`): RS_Ratio crosses above 100 while RS_Momentum > 100
  (fresh Leading-quadrant entry, matching the source's own highest-
  conviction "buy" heuristic of transitioning from Improving to Leading).
- Exit: RS_Ratio crosses back below 100 (Weakening -> Lagging transition,
  i.e. relative outperformance itself has broken down) or a max_hold_days
  safety time-stop.
- `generate_returns` requires BOTH `symbol` and `benchmark_symbol` price data
  to be passed in via a combined price_df with columns
  `close_<symbol_suffix>`/`close_<benchmark_suffix>` is NOT how grid_test.py
  calls strategies (single price_df, single symbol) -- so this strategy
  fetches its own benchmark series internally via `data/loaders.py` using
  `benchmark_asset_class`/`benchmark_symbol` params, keeping the
  grid_test.py single-price_df-arg contract intact for the primary `symbol`.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _wma(series: pd.Series, window: int) -> pd.Series:
    weights = pd.Series(range(1, window + 1), dtype=float)

    def _weighted(x):
        return (x * weights.values).sum() / weights.sum()

    return series.rolling(window).apply(_weighted, raw=True)


def _load_benchmark_close(
    benchmark_asset_class: str,
    benchmark_symbol: str,
    start,
    end,
) -> pd.Series:
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity, load_crypto  # noqa: E402

    loader = load_equity if benchmark_asset_class == "equity" else load_crypto
    bdf = loader(benchmark_symbol, start, end)
    bdf = _prep(bdf)
    return bdf["close"]


def _compute_rs_ratio_momentum(
    close: pd.Series,
    benchmark_close: pd.Series,
    wma_window: int,
    momentum_period: int,
) -> tuple[pd.Series, pd.Series]:
    aligned = pd.DataFrame({"close": close, "bench": benchmark_close}).dropna()
    rs = (aligned["close"] / aligned["bench"]) * 100.0

    rs_smooth = _wma(rs, wma_window)
    rs_benchmark_smooth = _wma(rs_smooth, wma_window)
    rs_ratio = (rs_smooth / rs_benchmark_smooth) * 100.0

    rs_momentum = (rs_ratio / rs_ratio.shift(momentum_period)) * 100.0

    rs_ratio = rs_ratio.reindex(close.index)
    rs_momentum = rs_momentum.reindex(close.index)
    return rs_ratio, rs_momentum


def generate_signals(
    price_df: pd.DataFrame,
    benchmark_asset_class: str = "crypto",
    benchmark_symbol: str = "BTC/USDT",
    wma_window: int = 10,
    momentum_period: int = 10,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series for the primary symbol,
    gated by its RRG Leading-quadrant status vs benchmark_symbol.
    """
    df = _prep(price_df)
    close = df["close"]

    start = close.index.min()
    end = close.index.max()
    benchmark_close = _load_benchmark_close(benchmark_asset_class, benchmark_symbol, start, end)

    rs_ratio, rs_momentum = _compute_rs_ratio_momentum(close, benchmark_close, wma_window, momentum_period)

    leading = (rs_ratio > 100.0) & (rs_momentum > 100.0)
    ratio_below_100 = rs_ratio <= 100.0

    leading = leading.fillna(False)
    ratio_below_100 = ratio_below_100.fillna(True)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(ratio_below_100.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(leading.iloc[i]):
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
