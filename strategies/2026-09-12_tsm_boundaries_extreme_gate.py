"""Strategy: 12-month time-series momentum, gated OFF near trailing-return
valuation-extreme proxy ("Boundaries" adaptation).

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per Suominen & Hjalmarsson's "Boundaries of Time Series Momentum" (SSRN
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6867878, summarized by
Quantpedia at https://quantpedia.com/boundaries-of-time-series-momentum/):
12-month equity time-series momentum performs well in MID-valuation
regimes but breaks down/reverses near historical valuation EXTREMES
(measured via CAPE, dividend yield, and term-spread moving averages in the
paper). That exact "Boundaries" variable needs CAPE/dividend-yield/
term-spread data unavailable via this repo's yfinance/ccxt OHLCV-only
loaders (same feasibility class as TRIN/McClellan/breadth-data blocks).
This strategy adapts the paper's core INSIGHT using a pure price-based
proxy that IS directly observable per-asset: gate a standard 12-month
absolute-momentum strategy OFF whenever the trailing 12-month return
itself sits at a historical percentile extreme (either very high or very
low, over a long rolling lookback) -- an extreme realized 12-month move is
a same-asset-native signal correlated with the valuation-extreme
conditions the paper identifies as breakdown zones, without requiring
external macro data.

Signal logic
------------
- 12-month momentum: `mom_12m` = 252-day trailing return.
- Historical percentile: rolling percentile rank of `mom_12m` over a long
  lookback (`percentile_window`, default 5 years = ~1260 trading days).
- "Mid-valuation regime" (tradeable): percentile rank is between
  `pct_lo` and `pct_hi` (e.g. 15th-85th percentile -- excludes the extreme
  tails where the paper found momentum breaks down).
- Long entry: `mom_12m` > 0 AND in the mid-valuation/tradeable regime.
- Flat otherwise (both when momentum is negative and when in an extreme
  regime, per the paper's own framing that direction doesn't matter near
  extremes -- reversals happen regardless of momentum sign).
- Monthly rebalance (following standard TSM convention -- signal only
  re-evaluated on the first trading day of each calendar month) to avoid
  excessive daily whipsaw on a 12-month signal.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
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


def _rolling_percentile_rank(values: np.ndarray, window: int) -> np.ndarray:
    """Vectorized-ish rolling percentile rank of the LAST value in each
    trailing window (fraction of window values <= last value)."""
    n = len(values)
    out = np.full(n, np.nan)
    for i in range(window - 1, n):
        seg = values[i - window + 1 : i + 1]
        valid = seg[~np.isnan(seg)]
        if len(valid) < max(5, window // 2):
            continue
        last = values[i]
        if np.isnan(last):
            continue
        out[i] = (valid <= last).sum() / len(valid)
    return out


def generate_signals(
    price_df: pd.DataFrame,
    lookback_days: int = 252,
    percentile_window: int = 756,
    pct_lo: float = 0.15,
    pct_hi: float = 0.85,
) -> pd.Series:
    """Return a {0,1} long/flat position series, monthly-rebalanced."""
    df = _prep(price_df)
    close = df["close"]

    mom_12m = close.pct_change(lookback_days)
    pct_rank = pd.Series(
        _rolling_percentile_rank(mom_12m.to_numpy(dtype=float), percentile_window),
        index=close.index,
    )

    mid_regime = (pct_rank >= pct_lo) & (pct_rank <= pct_hi)
    raw_signal = (mom_12m > 0) & mid_regime & mom_12m.notna() & pct_rank.notna()

    # Monthly rebalance: only re-evaluate the signal on the first trading
    # day of each calendar month; hold that decision through the month.
    month_key = close.index.tz_localize(None).to_period("M") if close.index.tz is not None else close.index.to_period("M")
    is_new_month = pd.Series(month_key, index=close.index).ne(pd.Series(month_key, index=close.index).shift(1))

    position = pd.Series(0, index=close.index, dtype=int)
    current = 0
    for i in range(len(close)):
        if is_new_month.iloc[i] or i == 0:
            current = int(bool(raw_signal.iloc[i]))
        position.iloc[i] = current
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
