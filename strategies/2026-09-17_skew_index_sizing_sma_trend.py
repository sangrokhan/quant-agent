"""Strategy: SMA(trend_window) directional gate on the primary asset, with
continuous CBOE SKEW Index sizing overlay (inverse tail-risk-pricing dial) +
deadband, leverage-cap-aware for crypto.

Hypothesis (knowledge_base id TBD, this cron trigger):
This repo has 1 prior CBOE SKEW Index entry (2026-09-05-029, rejected): a
BINARY threshold gate that went flat whenever the rolling z-score of the
SKEW index exceeded an extreme threshold (>=1.0/1.5/2.0), otherwise stayed
fully long -- rejected across equity and crypto. Per
https://ecmsource.com/volatility-skew-and-smile-explained-why-otm-puts-cost-more/
(citing the Cboe SKEW whitepaper, already cited in the prior rejected
entry), the SKEW index measures the market's own pricing of tail risk via
the cost of OTM S&P 500 puts relative to ATM options -- a continuously
varying quantity, not naturally a binary on/off signal. This iteration
follows this repo's established "binary threshold -> continuous sizing
dial" rescue pattern (successful previously for DPO, Hurst, VHF, TII, RVI,
MAMA-FAMA spread, Kalman slope): instead of going flat above a hard
threshold, exposure scales smoothly and inversely with the SKEW index's own
rolling z-score (higher z = more elevated tail-risk pricing = lower
exposure), tanh-squashed, applied within an SMA(trend_window) uptrend gate
on the primary asset. First continuous-sizing SKEW-Index variant in this
repo.

Source: CBOE SKEW Index (^SKEW ticker, fetched via data/loaders.py::load_equity
which already wraps yfinance -- no new data-fetching logic needed) +
ecmsource.com's explainer of the index's construction/meaning.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).

NOTE: `price_df` passed in by the grid/validator harness is the PRIMARY
asset's OHLCV (QQQ/SPY/BTC/etc). The SKEW index series is fetched
internally via load_equity("^SKEW", ...) using the primary asset's own
date range, then reindexed/forward-filled onto the primary asset's trading
calendar (SKEW is a US-equity-index-options-derived series, published only
on US equity trading days -- crypto's 24/7 calendar gets the last known
SKEW value forward-filled across weekends/holidays, an accepted
approximation already used for other cross-asset regime-gate strategies in
this repo, e.g. Baltic Dry Index BDRY gate).
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _load_skew_series(index: pd.DatetimeIndex) -> pd.Series:
    """Fetch the CBOE SKEW index over the primary asset's date range and
    reindex/forward-fill it onto `index`. Imports load_equity lazily to
    avoid a hard import-time dependency on data/loaders.py's sys.path setup
    when this module is loaded standalone (e.g. by grid_test.py which
    already adds data/ to sys.path itself, or by a validator harness).
    """
    import sys
    import os

    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    if data_dir not in sys.path:
        sys.path.insert(0, data_dir)
    from loaders import load_equity  # noqa: E402

    start = index.min() - pd.Timedelta(days=10)
    end = index.max() + pd.Timedelta(days=2)
    skew_df = load_equity("^SKEW", start=start.to_pydatetime(), end=end.to_pydatetime())
    skew_df = skew_df.copy()
    if "timestamp" in skew_df.columns:
        skew_df = skew_df.set_index("timestamp")
    skew_df = skew_df.sort_index()
    skew_close = skew_df["close"]

    # Reindex onto the primary asset's calendar, ffill for gaps (weekends,
    # holidays, or crypto's 24/7 calendar vs SKEW's US-equity-only publish
    # schedule), then bfill any leading NaNs from the very start of history.
    aligned = skew_close.reindex(index.union(skew_close.index)).sort_index()
    aligned = aligned.ffill().bfill()
    aligned = aligned.reindex(index)
    return aligned


def _apply_deadband(raw_exposure: pd.Series, deadband: float) -> pd.Series:
    raw = raw_exposure.fillna(0.0).to_numpy()
    held = np.zeros_like(raw)
    current = 0.0
    for i, r in enumerate(raw):
        if abs(r - current) > deadband:
            current = r
        held[i] = current
    return pd.Series(held, index=raw_exposure.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    skew_zscore_window: int = 126,
    sensitivity: float = 0.5,
    base_exposure: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series, held constant
    within `deadband` of the last update to cut turnover.

    dial = -tanh(zscore(SKEW, skew_zscore_window)) -- higher/elevated SKEW
    (more tail-risk pricing) pushes the dial negative (reduce exposure);
    lower/calmer SKEW pushes it positive (increase exposure), gated to 0
    whenever close is below its SMA(trend_window).
    """
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    skew = _load_skew_series(close.index)
    roll_mean = skew.rolling(skew_zscore_window).mean()
    roll_std = skew.rolling(skew_zscore_window).std(ddof=0)
    z = (skew - roll_mean) / roll_std.replace(0.0, np.nan)
    dial = -np.tanh(z.fillna(0.0))

    raw_exposure = base_exposure + sensitivity * dial
    raw_exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap)
    raw_exposure = raw_exposure.where(trend_long.fillna(False), other=0.0)

    exposure = _apply_deadband(raw_exposure, deadband)
    return exposure


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 40,
    skew_zscore_window: int = 126,
    sensitivity: float = 0.5,
    base_exposure: float = 0.5,
    leverage_cap: float = 1.0,
    deadband: float = 0.20,
) -> pd.Series:
    """Daily strategy returns: prior-day exposure * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(
        price_df,
        trend_window=trend_window,
        skew_zscore_window=skew_zscore_window,
        sensitivity=sensitivity,
        base_exposure=base_exposure,
        leverage_cap=leverage_cap,
        deadband=deadband,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strat_ret
