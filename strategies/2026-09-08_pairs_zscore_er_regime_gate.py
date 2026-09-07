"""Strategy: rolling-hedge-ratio cointegration z-score pairs trade, gated by
an Efficiency-Ratio-based volatility/trend regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-071, and
this iteration's own id): direct fix for near-miss 2026-09-08-071 (JPM/BAC
pairs z-score mean reversion, full-period Sharpe 0.954 vs 1.0 threshold),
whose own grid test showed the edge concentrated almost entirely in the
low-vol tercile (16/18 low-vol cells passed vs 3/18 mid, 2/18 high). Per
https://www.tradewink.com/learn/mean-reversion-volatility-regime-guide,
mean-reversion signals should be suppressed during trending/high-momentum
regimes and only fired during range-bound/choppy regimes, quantified via
Kaufman's Efficiency Ratio (ER, already used elsewhere in this repo for
trend-following gates, e.g. 2026-09-04-120/151 -- here reused for the
OPPOSITE purpose: gating a mean-reversion trade IN when ER is LOW i.e.
choppy/range-bound, rather than gating a trend trade in when ER is HIGH).
Per the source's own suggested threshold, ER < 0.35 indicates a
range-bound/favorable-for-reversion regime.

Signal logic
------------
Identical spread/z-score construction to 2026-09-08_pairs_zscore_cointegration.py,
plus an added gate:
- Kaufman Efficiency Ratio computed on the PRIMARY symbol's own close price
  over er_period bars: ER = |close - close[t-er_period]| / sum(|diff(close)|
  over the same window). Range 0 (pure noise/chop) to 1 (pure efficient trend).
- Entry (long the spread): z-score <= -entry_z AND ER <= er_threshold
  (only take the mean-reversion trade when the primary symbol itself is in
  a choppy/range-bound regime, not a strong trend that could keep pushing
  the spread further apart).
- Exit: z-score reverts to >= -exit_z, OR ER rises above er_threshold
  (regime flip to trending -- risk-off exit), OR max_hold_days time-stop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _load_partner(index: pd.DatetimeIndex, asset_class: str, partner_symbol: str) -> pd.Series:
    """Fetch the partner leg's close series over price_df's date range."""
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity, load_crypto  # noqa: E402

    start = index.min()
    end = index.max() + timedelta(days=2)
    if asset_class == "crypto":
        partner_df = load_crypto(partner_symbol, start, end)
    else:
        partner_df = load_equity(partner_symbol, start, end)
    partner_df = _prep(partner_df)
    return partner_df["close"]


def _spread_zscore(
    price_df: pd.DataFrame,
    asset_class: str,
    partner_symbol: str,
    hedge_window: int,
    z_window: int,
) -> pd.Series:
    df = _prep(price_df)
    close_a = df["close"]
    close_b = _load_partner(df.index, asset_class, partner_symbol)
    close_b = close_b.reindex(close_a.index).ffill()

    log_a = np.log(close_a)
    log_b = np.log(close_b)

    cov = log_a.rolling(hedge_window).cov(log_b)
    var_b = log_b.rolling(hedge_window).var()
    beta = cov / var_b

    spread = log_a - beta * log_b
    spread_mean = spread.rolling(z_window).mean()
    spread_std = spread.rolling(z_window).std()
    z = (spread - spread_mean) / spread_std
    return z.replace([np.inf, -np.inf], np.nan)


def _efficiency_ratio(close: pd.Series, er_period: int) -> pd.Series:
    net_change = (close - close.shift(er_period)).abs()
    path_length = close.diff().abs().rolling(er_period).sum()
    er = net_change / path_length
    return er.replace([np.inf, -np.inf], np.nan)


def generate_signals(
    price_df: pd.DataFrame,
    asset_class: str = "equity",
    partner_symbol: str = "BAC",
    hedge_window: int = 90,
    z_window: int = 15,
    entry_z: float = 1.5,
    exit_z: float = 0.3,
    max_hold_days: int = 15,
    er_period: int = 20,
    er_threshold: float = 0.35,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    z = _spread_zscore(price_df, asset_class, partner_symbol, hedge_window, z_window)
    z = z.reindex(df.index)
    er = _efficiency_ratio(close, er_period).reindex(df.index)
    range_bound = er <= er_threshold

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_days = 0
    for i in range(len(df.index)):
        zt = z.iloc[i]
        rb = range_bound.iloc[i]
        if in_position:
            hold_days += 1
            if pd.isna(zt) or zt >= -exit_z or hold_days >= max_hold_days or not bool(rb):
                in_position = False
                hold_days = 0
            else:
                position.iloc[i] = 1
        else:
            if not pd.isna(zt) and zt <= -entry_z and bool(rb) and not pd.isna(rb):
                in_position = True
                hold_days = 1
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    asset_class: str = "equity",
    partner_symbol: str = "BAC",
    hedge_window: int = 90,
    z_window: int = 15,
    entry_z: float = 1.5,
    exit_z: float = 0.3,
    max_hold_days: int = 15,
    er_period: int = 20,
    er_threshold: float = 0.35,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_returns = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df,
        asset_class=asset_class,
        partner_symbol=partner_symbol,
        hedge_window=hedge_window,
        z_window=z_window,
        entry_z=entry_z,
        exit_z=exit_z,
        max_hold_days=max_hold_days,
        er_period=er_period,
        er_threshold=er_threshold,
    )
    strat_returns = daily_returns * position.shift(1).fillna(0)
    return strat_returns
