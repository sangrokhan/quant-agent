"""Strategy: Sector-Leadership Regime Gate via JdK RS-Ratio / RS-Momentum
"leading quadrant" (Relative Rotation Graph construction).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-10-003):
Per StockCharts ChartSchool's RRG Relative Strength explainer
(https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/rrg-relative-strength),
Relative Rotation Graphs classify a security's relative performance vs a
benchmark into four quadrants using two normalized (both centered on 100)
indicators: JdK RS-Ratio (the smoothed TREND of relative performance --
above 100 = relative strength/uptrend, below 100 = relative
weakness/downtrend) and JdK RS-Momentum (the rate-of-change / MOMENTUM of
RS-Ratio -- leads RS-Ratio, anticipating its turns). A security is in the
"leading" quadrant -- the strongest, most favorable state -- when BOTH
RS-Ratio and RS-Momentum are above 100 simultaneously.

This repo already tested a SOXX/QQQ semiconductor-leadership regime gate
using a raw single-indicator pct_change ROC threshold
(2026-09-09-118/119/120, final version accepted for both QQQ and SPY).
This strategy is a DISTINCT construction of the same "does a
leading/lagging sector or asset ratio predict broad-market regime"
family: instead of one raw ROC threshold, it uses RRG's own two-indicator
normalized RS-Ratio/RS-Momentum "leading quadrant" definition -- a
double-smoothed, trend-of-trend construction that per the source's own
description reacts more slowly than raw price/ratio momentum but is
designed specifically to filter out noise/blips that a single ROC
threshold would react to.

Construction (adapted to daily OHLCV, single-pair regime gate rather than
StockCharts' full multi-sector RRG chart):
- Base symbol XLK (Technology Sector SPDR), benchmark symbol SPY (S&P 500
  proxy) -- XLK/SPY relative price ratio.
- rs = 100 * (XLK_close / SPY_close), reindexed/aligned to the traded
  asset's own bar index.
- RS-Ratio = 100 * (1 + (rs - SMA(rs, rs_window)) / SMA(rs, rs_window))
  -- a percent-of-trailing-SMA normalization producing a series centered
  on 100 (a standard open-source approximation of JdK's proprietary
  double-smoothing formula, since the exact StockCharts formula is not
  publicly disclosed).
- RS-Momentum = 100 * (1 + (RS-Ratio - RS-Ratio.shift(mom_window)) /
  RS-Ratio.shift(mom_window)) -- the rate-of-change of RS-Ratio itself,
  also centered on 100.
- Leading quadrant / risk-on = RS-Ratio > 100 AND RS-Momentum > 100.
- Long the traded asset (QQQ/SPY/BTC/ETH) whenever in the leading
  quadrant; flat otherwise. No separate broad-trend SMA filter this
  iteration (tests the RRG quadrant construction on its own merits first,
  the way the SOXX/QQQ lineage's first entry 2026-09-09-118 tested the
  plain ROC gate alone before layering a trend filter in the 119/120
  follow-ups).

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
"""

from __future__ import annotations

import sys
import os

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_leading_quadrant(
    idx: pd.DatetimeIndex, rs_window: int, mom_window: int
) -> pd.Series:
    from loaders import load_equity

    lookback_days = (rs_window + mom_window) * 3 + 60
    start = (idx.min() - pd.Timedelta(days=lookback_days)).to_pydatetime()
    end = (idx.max() + pd.Timedelta(days=5)).to_pydatetime()

    base = load_equity("XLK", start, end).set_index("timestamp")["close"].sort_index()
    bench = load_equity("SPY", start, end).set_index("timestamp")["close"].sort_index()
    base.index = base.index.tz_localize(None) if base.index.tz is not None else base.index
    bench.index = bench.index.tz_localize(None) if bench.index.tz is not None else bench.index

    common_idx = base.index.intersection(bench.index)
    rs = 100.0 * (base.reindex(common_idx) / bench.reindex(common_idx))

    rs_sma = rs.rolling(rs_window, min_periods=rs_window).mean()
    rs_ratio = 100.0 * (1.0 + (rs - rs_sma) / rs_sma)

    rs_ratio_lag = rs_ratio.shift(mom_window)
    rs_momentum = 100.0 * (1.0 + (rs_ratio - rs_ratio_lag) / rs_ratio_lag)

    leading = (rs_ratio > 100.0) & (rs_momentum > 100.0)

    target_idx = idx.tz_localize(None) if getattr(idx, "tz", None) is not None else idx
    leading = leading.reindex(leading.index.union(target_idx)).sort_index().ffill()
    leading = leading.reindex(target_idx)
    leading.index = idx
    return leading


def generate_signals(
    price_df: pd.DataFrame,
    rs_window: int = 20,
    mom_window: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long whenever the base/benchmark (XLK/SPY) relative-strength pair is in
    the RRG "leading" quadrant (RS-Ratio>100 AND RS-Momentum>100); flat
    otherwise.
    """
    df = _prep(price_df)
    idx = df.index

    try:
        leading = _get_leading_quadrant(idx, rs_window, mom_window)
    except Exception:
        leading = pd.Series(False, index=idx)

    position = leading.fillna(False).astype(int)
    position.index = idx
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
