"""Strategy: OVX (Cboe Crude Oil ETF Volatility Index) z-score regime gate on
a USO (WTI crude oil ETF) trend-following signal.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-115):
Per StoneX's OVX explainer (https://www.stonex.com/en/news-and-analysis/2023/10/ovx-index-your-guide-to-the-oil-volatility-index/,
read via browser_exec after web_search DDGS/Yahoo backend TLS-errored on
this iteration's queries), OVX -- unlike the VIX's negative correlation with
equities -- tends to move WITH oil prices during genuine fear spikes:
"increased fear usually drives oil prices upwards, unlike the VIX which has
a negative correlation to the price of equities" because oil-market fear is
usually driven by supply-shock/geopolitical risk, which is bullish for
crude. This repo has never tested a crude-oil-volatility-index gate (first
OVX strategy; 0 prior matches in strategies_index.jsonl for "OVX"). We
adapt the source's directional claim into this repo's established
trend-gate construction: long USO's own SMA(trend_window) trend-following
signal only when OVX's rolling z-score (vs its own trailing history) is
ABOVE a rising-fear threshold (the opposite sign convention from every
VIX-based equity regime gate already tested here, which typically goes
risk-off on HIGH VIX z-score) -- i.e. elevated oil-specific volatility is
read as a bullish confirming signal for crude, not a risk-off flag.

Signal logic
------------
- USO's own long-term trend: close > SMA(trend_window) -> uptrend.
- OVX rolling z-score: (OVX_close - rolling_mean(zscore_window)) /
  rolling_std(zscore_window).
- Long only when BOTH: USO in an uptrend AND OVX z-score >= ovx_z_threshold
  (elevated-but-not-extreme oil-fear regime, source's stated bullish-for-oil
  read). Flat otherwise (including when OVX z-score is deeply negative /
  complacent, since the source's mechanism requires an active fear spike,
  not merely "not fearful").

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series

Both fetch OVX internally via data/loaders.py load_equity("^OVX", ...) using
the price_df's own index range, so the grid-test harness (which only passes
the primary symbol's price_df) still works unmodified. price_df is expected
to be the PRIMARY (USO-equivalent) asset's OHLCV; for other symbols (QQQ,
SPY, BTC/USDT, ETH/USDT) this same OVX-fear-gate construction is tested as
an explicit cross-asset-transferability check, since the source's economic
mechanism (oil-specific fear -> oil-specific relief rally) doesn't obviously
carry over -- expected to fail outside crude-oil-linked assets, but tested
per the repo's standard cross-asset-class grid protocol.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_ovx(index: pd.DatetimeIndex) -> pd.Series:
    """Fetch ^OVX aligned to the given index, forward-filled for any gaps."""
    from loaders import load_equity  # local import to avoid hard dependency at module load

    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()
    ovx_df = load_equity("^OVX", start, end)
    ovx_df = _prep(ovx_df)
    ovx_close = ovx_df["close"]
    # Align to the target index: reindex + ffill/bfill for any date mismatches
    ovx_aligned = ovx_close.reindex(index.union(ovx_close.index)).sort_index()
    ovx_aligned = ovx_aligned.ffill().bfill()
    ovx_aligned = ovx_aligned.reindex(index)
    return ovx_aligned


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 100,
    zscore_window: int = 60,
    ovx_z_threshold: float = 0.5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    ovx = _load_ovx(close.index)
    ovx_mean = ovx.rolling(zscore_window).mean()
    ovx_std = ovx.rolling(zscore_window).std()
    import numpy as np

    ovx_std_safe = ovx_std.replace(0, np.nan)
    ovx_z = (ovx - ovx_mean) / ovx_std_safe
    ovx_z = ovx_z.astype(float)

    fear_gate = ovx_z >= ovx_z_threshold
    entry_condition = uptrend.fillna(False) & fear_gate.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            exit_now = (not bool(entry_condition.iloc[i])) or held >= max_hold_days
            if exit_now:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_condition.iloc[i]):
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
