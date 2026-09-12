"""Strategy: Volatility-adjusted multi-horizon cross-sectional crypto
momentum portfolio (BTC/ETH/SOL, long-only weighted allocation).

Source: GitHub VASUDHA-SRIPERAMBUDURU/volatility-adjusted-crypto-momentum
(https://github.com/VASUDHA-SRIPERAMBUDURU/volatility-adjusted-crypto-momentum,
full source read this iteration via browser_exec -- web_search DDGS
backend used for discovery this iteration, browser_exec used to read the
GitHub README and raw .py source directly). Disclosed formula (adapted
long-only per this repo's SAFETY.md -- the original allows negative/short
weights via signed score normalization, which this repo never implements):

    momentum_7/14/30 = rolling `N`-day sum of log returns
    combined_momentum = mean(momentum_7, momentum_14, momentum_30)
    score = combined_momentum / rolling_vol_window-day std of log returns,
            clipped to [-score_clip, score_clip]
    score_long = max(score, 0)  (long-only adaptation: zero out negative
        scores instead of allowing short positions)
    weight[asset] = score_long[asset] / sum(score_long) if sum>0 else 0
    weight *= exposure_scale (source default 0.5)
    weight *= high_vol_derate if market-average rolling vol is above its
        own trailing vol_regime_quantile (source default 0.75, applies an
        additional 0.5x cut) -- source's own "reduce aggressiveness in
        high-vol regimes" risk control.
    Weekly rebalance (source default), 0.1%-of-turnover transaction cost
    already handled by this repo's Step 7 TC-survival validator rather
    than baked into generate_returns.

This is architecturally distinct from this cron trigger's earlier,
decisively-rejected 2026-09-13-035/036 (always-invested WINNER-TAKE-ALL
single-asset rotation): this strategy instead holds a WEIGHTED portfolio
across all three assets simultaneously, proportional to each asset's
vol-adjusted relative momentum, with an explicit market-wide high-vol
de-risking overlay and a fixed 50% baseline exposure scale-down (partial
cash position even in the best case) -- a fundamentally different (and
per -035/036's own diagnosis, likely much lower-drawdown) risk
construction than concentrating 100% in whichever single asset is
currently "hottest".

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series (total invested
        exposure fraction, 0.0-1.0*exposure_scale, i.e. sum of the three
        asset weights -- NOT a binary/{0,1,2,3} position label since this
        is a weighted multi-asset portfolio)
    generate_returns(price_df, **params) -> pd.Series (daily
        weighted-portfolio strategy returns)

Note: `price_df` here is expected to be BTC/USDT's OHLCV (the "primary"
symbol passed by the grid harness); ETH/USDT and SOL/USDT are fetched
internally via data/loaders.py.
"""

from __future__ import annotations

import sys
import os

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_crypto  # noqa: E402


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _simulate(
    price_df: pd.DataFrame,
    vol_window: int = 20,
    score_clip: float = 5.0,
    exposure_scale: float = 0.5,
    vol_regime_quantile: float = 0.75,
    high_vol_derate: float = 0.5,
    rebalance_days: int = 5,
) -> pd.DataFrame:
    """`price_df` is treated as BTC/USDT's OHLCV; ETH/USDT and SOL/USDT are
    fetched internally as the other two portfolio constituents."""
    btc_df = _prep(price_df)
    btc_close = btc_df["close"]
    start, end = btc_df.index.min(), btc_df.index.max()
    if getattr(start, "tzinfo", None) is not None:
        start = start.tz_localize(None)
    if getattr(end, "tzinfo", None) is not None:
        end = end.tz_localize(None)

    eth_close = _prep(load_crypto("ETH/USDT", start, end))["close"].reindex(btc_close.index, method="ffill")
    sol_close = _prep(load_crypto("SOL/USDT", start, end))["close"].reindex(btc_close.index, method="ffill")

    closes = pd.DataFrame({"BTC": btc_close, "ETH": eth_close, "SOL": sol_close})
    log_ret = np.log(closes / closes.shift(1))

    mom7 = log_ret.rolling(7).sum()
    mom14 = log_ret.rolling(14).sum()
    mom30 = log_ret.rolling(30).sum()
    combined_momentum = (mom7 + mom14 + mom30) / 3.0

    rolling_vol = log_ret.rolling(vol_window).std()
    score = (combined_momentum / rolling_vol).clip(-score_clip, score_clip)

    # Long-only adaptation: zero out negative scores (no shorting per SAFETY.md).
    score_long = score.clip(lower=0.0)
    score_sum = score_long.sum(axis=1)
    weights = score_long.div(score_sum.replace(0, np.nan), axis=0).fillna(0.0)

    weights = weights * exposure_scale

    market_vol = rolling_vol.mean(axis=1)
    vol_threshold = market_vol.expanding(min_periods=vol_window * 2).quantile(vol_regime_quantile)
    high_vol_regime = (market_vol > vol_threshold).fillna(False)
    weights = weights.mul(np.where(high_vol_regime, high_vol_derate, 1.0), axis=0)

    # Weekly (rebalance_days) rebalance: hold prior rebalance's weights
    # between rebalance dates instead of drifting continuously.
    n = len(weights)
    rebalanced = weights.copy()
    if rebalance_days > 1:
        held_weights = weights.iloc[0:1].copy()
        result = []
        current = weights.iloc[0]
        for i in range(n):
            if i % rebalance_days == 0:
                current = weights.iloc[i]
            result.append(current)
        rebalanced = pd.DataFrame(result, index=weights.index, columns=weights.columns)

    simple_ret = closes.pct_change().fillna(0.0)
    weights_shifted = rebalanced.shift(1).fillna(0.0)
    strat_ret = (weights_shifted * simple_ret).sum(axis=1)
    total_exposure = rebalanced.sum(axis=1)

    return pd.DataFrame({"position": total_exposure, "returns": strat_ret}, index=btc_close.index)


def generate_signals(
    price_df: pd.DataFrame,
    vol_window: int = 20,
    score_clip: float = 5.0,
    exposure_scale: float = 0.5,
    vol_regime_quantile: float = 0.75,
    high_vol_derate: float = 0.5,
    rebalance_days: int = 5,
) -> pd.Series:
    return _simulate(
        price_df,
        vol_window=vol_window,
        score_clip=score_clip,
        exposure_scale=exposure_scale,
        vol_regime_quantile=vol_regime_quantile,
        high_vol_derate=high_vol_derate,
        rebalance_days=rebalance_days,
    )["position"]


def generate_returns(
    price_df: pd.DataFrame,
    vol_window: int = 20,
    score_clip: float = 5.0,
    exposure_scale: float = 0.5,
    vol_regime_quantile: float = 0.75,
    high_vol_derate: float = 0.5,
    rebalance_days: int = 5,
) -> pd.Series:
    return _simulate(
        price_df,
        vol_window=vol_window,
        score_clip=score_clip,
        exposure_scale=exposure_scale,
        vol_regime_quantile=vol_regime_quantile,
        high_vol_derate=high_vol_derate,
        rebalance_days=rebalance_days,
    )["returns"]
