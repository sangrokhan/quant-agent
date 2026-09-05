"""Strategy: Growth-vs-Value (IVW/IVE) ratio SMA regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-068):
Per ETFreplay's "Regime Change" blog (etfreplay.com/blog/regime-change/,
"Ratio MA Composite example: Growth vs Value"): "Using a ratio of Growth
to Value securities naturally shows which of these two market segments is
the strongest. When Growth outperforms Value the ratio will rise; when
Growth is underperforming the ratio will fall." Source's own backtest
methodology: invest in the numerator (Growth) when the ratio is above its
own N-month moving average (trending up), switch to the denominator
(Value)/flat otherwise; source found a 4-month MA (~80 trading days)
outperformed shorter/longer windows on their own SCHG/FNDX sample.

This repo operationalizes it as a binary long/flat regime gate on the
strategy's OWN underlying (QQQ/SPY/etc.) rather than switching between two
different ETFs (source's own dual-holding design), using the standard
large-cap Growth/Value ETF pair (IVW/IVE, S&P 500 Growth/Value, longer
history than SCHG/FNDX) since data/loaders.py only fetches single-series
OHLCV: long the underlying while IVW/IVE ratio > its own ma_window-day
SMA (Growth outperforming = broad risk-on breadth), flat otherwise. First
Growth/Value-ratio strategy in this repo -- distinct from all other
cross-asset ratio regime filters tested (gold/silver, copper/gold,
XLY/XLP, IWM/SPY, RSP/SPY, SPY/TLT, XLU/SPY).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly). IVW/IVE data is
fetched internally via data/loaders.py.load_equity (cache-first), keyed
off the same date range as price_df.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in price_df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_ratio_series(symbol: str, start, end) -> pd.Series:
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity  # noqa: E402

    df = load_equity(symbol, start, end)
    df = df.set_index("timestamp") if "timestamp" in df.columns else df
    return df.sort_index()["close"]


def generate_signals(
    price_df: pd.DataFrame,
    ma_window: int = 80,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long (risk-on) when the IVW/IVE (Growth/Value) ratio is above its own
    ma_window-day SMA (Growth outperforming, trending up); flat otherwise.
    """
    df = _prep(price_df)
    close = df["close"]

    start = close.index.min()
    end = close.index.max()
    ivw = _load_ratio_series("IVW", start, end).reindex(close.index).ffill()
    ive = _load_ratio_series("IVE", start, end).reindex(close.index).ffill()

    ratio = ivw / ive
    sma = ratio.rolling(ma_window).mean()

    growth_leading = ratio > sma
    position = growth_leading.fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
