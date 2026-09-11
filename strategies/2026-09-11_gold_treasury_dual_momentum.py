"""Strategy: Gold Cross-Asset Momentum (Gold + 10yr Treasury dual absolute
momentum gate).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-082):
Per QuantifiedStrategies.com's "7 Best Algo Trading Strategies for
Beginners" (https://www.quantifiedstrategies.com/7-best-algo-trading-strategies-for-beginners/,
visited this iteration), the source's own disclosed "Gold Momentum
Strategy" rule: go long GLD only when BOTH GLD's own trailing 12-month
total return AND the 10-year Treasury proxy (IEF)'s trailing 12-month
total return are positive; move to cash if EITHER asset shows a negative
12-month return. Source's own backtest (5 decades, presumably via GLD's
1970s gold-price proxy + more recent IEF data): annualized return 11.5%
vs buy-and-hold gold's higher absolute return but with max drawdown 31%
vs buy-and-hold's 64% -- i.e. the source's own claimed edge is DRAWDOWN
REDUCTION via a dual-confirmation absolute-momentum filter, not return
enhancement (source itself notes the edge "waned" since ~2002 on raw
return terms).

This is a genuinely new indicator-family combination in this repo: no
prior strategy gates GOLD's own position using a TREASURY BOND's absolute
momentum as a confirming co-signal (distinct from GLD/SLV ratio pairs,
GLD-as-a-gate-on-other-assets like 2026-09-08-147, or TLT-based regime
gates on equities). Applied here with GLD as price_df AND, for the
grid's asset-class-generalization test, also run on QQQ/SPY/crypto to see
if the dual-confirmation absolute-momentum-of-a-DIFFERENT-pair construct
generalizes as a general "risk-on gate" beyond gold itself.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _trailing_12mo_return(close: pd.Series, lookback_days: int) -> pd.Series:
    return close.pct_change(lookback_days)


def _get_ief_momentum(index: pd.DatetimeIndex, lookback_days: int) -> pd.Series:
    """Load IEF (10yr Treasury proxy) via data/loaders.py and compute its
    trailing lookback_days-day return, aligned/ffilled to `index`."""
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity  # noqa: E402

    start = (index.min() - pd.Timedelta(days=lookback_days * 2 + 30)).to_pydatetime()
    end = (index.max() + pd.Timedelta(days=10)).to_pydatetime()

    df = load_equity("IEF", start, end)
    close = df.set_index("timestamp")["close"] if "timestamp" in df.columns else df["close"]
    close = close[~close.index.duplicated(keep="last")].sort_index()
    ief_mom = _trailing_12mo_return(close, lookback_days)

    is_naive = pd.DatetimeIndex(index).tz is None
    ief_idx_naive = ief_mom.index.tz_localize(None) if ief_mom.index.tz is not None else ief_mom.index
    target_idx_naive = pd.DatetimeIndex(index).tz_localize(None) if not is_naive else pd.DatetimeIndex(index)
    ief_mom_naive = ief_mom.copy()
    ief_mom_naive.index = ief_idx_naive
    aligned = ief_mom_naive.reindex(target_idx_naive, method="ffill")
    aligned.index = index
    return aligned


def generate_signals(
    price_df: pd.DataFrame,
    lookback_days: int = 252,
    min_hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series: long the primary asset
    (intended GLD) only when BOTH the primary asset's own trailing
    lookback_days return AND IEF's trailing lookback_days return are
    positive; flat otherwise. `min_hold_days` prevents daily flip-flop
    noise around the zero-crossing (a modest robustness addition not in
    the source's own disclosed rule, which appears to check monthly)."""
    df = _prep(price_df)
    close = df["close"]

    primary_mom = _trailing_12mo_return(close, lookback_days)
    ief_mom = _get_ief_momentum(close.index, lookback_days)

    raw_long = (primary_mom > 0) & (ief_mom > 0)
    raw_long = raw_long.fillna(False)

    # Apply a minimum-hold smoothing: only flip position if the raw signal
    # has been stable for min_hold_days consecutive days (reduces whipsaw
    # right at the 12-month-return zero-crossing).
    position = pd.Series(0, index=close.index, dtype=int)
    current = 0
    streak_val = None
    streak_len = 0
    for i in range(len(close)):
        val = bool(raw_long.iloc[i])
        if val == streak_val:
            streak_len += 1
        else:
            streak_val = val
            streak_len = 1
        if streak_len >= min_hold_days and val != bool(current):
            current = 1 if val else 0
        position.iloc[i] = current
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strategy_ret
