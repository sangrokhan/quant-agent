"""Strategy: 3-factor market-regime allocation (Trend / Volatility-Term-
Structure / Credit-Risk-Appetite), applied to the traded asset itself,
scaling exposure to 100%/50%/0% by how many of the 3 conditions are
favorable.

Hypothesis (knowledge_base id TBD, this cron trigger):
Per TASC July 2026 "Market Regime Identification Using Trend, Volatility,
And Credit Conditions" (Gaetano Di Prima & Fabio Baruffa), re-implemented
in the open-source TradingView script
https://www.tradingview.com/script/wu1VhNpf-TASC-2026-07-Risk-On-Risk-Off-Or-Caution/
(visited this iteration -- full disclosed rules read directly from the
script's overview text). The regime classification combines three
binary conditions, assessed weekly:

1. Trend Filter: SPX (or the traded asset itself, per this repo's
   single-symbol adaptation) above its own 200-day SMA -> favorable.
2. Volatility Filter: VIX < VIX3M (near-term implied vol below the
   3-month term structure point -- i.e. the vol curve is in normal
   contango, not stressed/inverted backwardation) -> favorable.
3. Risk Appetite (credit): the 100-day SMA of the rolling z-score of the
   HYG/IEF (high-yield credit vs 7-10yr Treasury) price ratio is positive
   -> favorable.

Rules: if all 3 favorable, full exposure (leverage_cap); if 2/3
favorable, 50% exposure; if 1/3 or 0/3 favorable, flat. Source's own
strategy trades SPY specifically; this repo applies the SAME 3-factor
macro regime signal (computed once from SPX/VIX/VIX3M/HYG/IEF, independent
of which asset it gates) to whichever symbol ``price_df`` represents,
including crypto, to test whether a macro-only (no asset-specific
technical) regime signal generalizes beyond SPY. First strategy in this
repo combining a VIX-term-structure filter with a credit-appetite filter
in one composite regime score (distinct from prior single-factor
credit-spread/HYG-IEF-only filters, e.g. 2026-09-05-025's HYG/LQD z-score
regime gate and 2026-09-10-024's HYG/IEF GEM rotation, and distinct from
prior VIX-only or trend-only filters).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (discrete exposure
    in {0, 0.5*leverage_cap, leverage_cap}).
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


def _load_macro_series(index: pd.DatetimeIndex) -> dict:
    """Fetch SPX, VIX, VIX3M, HYG, IEF closes over price_df's date range,
    reindexed/ffilled onto ``index``."""
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    from loaders import load_equity  # noqa: E402

    start = index.min() - timedelta(days=260)  # extra lookback for 200d SMA / z-score
    end = index.max() + timedelta(days=2)

    def _close(symbol: str) -> pd.Series:
        d = _prep(load_equity(symbol, start, end))
        return d["close"]

    spx = _close("^GSPC")
    vix = _close("^VIX")
    vix3m = _close("^VIX3M")
    hyg = _close("HYG")
    ief = _close("IEF")
    return {"spx": spx, "vix": vix, "vix3m": vix3m, "hyg": hyg, "ief": ief}


def _regime_score(index: pd.DatetimeIndex, trend_window: int = 200, credit_window: int = 100) -> pd.Series:
    """Number of favorable conditions (0/1/2/3) at each date in ``index``,
    per the disclosed TASC 2026.07 rule set."""
    macro = _load_macro_series(index)
    spx, vix, vix3m, hyg, ief = (
        macro["spx"],
        macro["vix"],
        macro["vix3m"],
        macro["hyg"],
        macro["ief"],
    )

    # Union index across all 5 macro series (different symbols/exchanges
    # may have slightly different trading-day calendars), forward-filled,
    # before computing cross-series conditions.
    common_index = spx.index.union(vix.index).union(vix3m.index).union(hyg.index).union(ief.index)
    spx = spx.reindex(common_index).ffill()
    vix = vix.reindex(common_index).ffill()
    vix3m = vix3m.reindex(common_index).ffill()
    hyg = hyg.reindex(common_index).ffill()
    ief = ief.reindex(common_index).ffill()

    trend_sma = spx.rolling(trend_window, min_periods=trend_window).mean()
    trend_ok = (spx > trend_sma).astype(int)

    vol_ok = (vix < vix3m).astype(int)

    ratio = hyg / ief
    ratio_mean = ratio.rolling(credit_window, min_periods=credit_window).mean()
    ratio_std = ratio.rolling(credit_window, min_periods=credit_window).std()
    z = (ratio - ratio_mean) / ratio_std.replace(0.0, np.nan)
    z_sma = z.rolling(credit_window, min_periods=credit_window).mean()
    credit_ok = (z_sma > 0).astype(int)

    score = trend_ok.add(vol_ok, fill_value=0).add(credit_ok, fill_value=0)
    score = score.reindex(index, method="ffill")
    return score


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    credit_window: int = 100,
    leverage_cap: float = 1.0,
    rebalance_freq: str = "W",
) -> pd.Series:
    """Discrete exposure in {0, 0.5*leverage_cap, leverage_cap} based on
    how many of the 3 macro-regime conditions are favorable, resampled to
    ``rebalance_freq`` (default weekly, matching the source's own weekly
    rebalance cadence) and held flat between rebalances."""
    df = _prep(price_df)
    score = _regime_score(df.index, trend_window=trend_window, credit_window=credit_window)

    # Resample to weekly (Monday) decisions, then forward-fill within week,
    # matching the source's "assess at week end, execute Monday open" cadence.
    weekly_score = score.resample(rebalance_freq).last()
    weekly_score = weekly_score.reindex(df.index.union(weekly_score.index)).ffill()
    weekly_score = weekly_score.reindex(df.index)

    exposure = pd.Series(0.0, index=df.index)
    exposure[weekly_score >= 3] = leverage_cap
    exposure[weekly_score == 2] = 0.5 * leverage_cap
    exposure[weekly_score <= 1] = 0.0
    return exposure.fillna(0.0)


def generate_returns(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    credit_window: int = 100,
    leverage_cap: float = 1.0,
    rebalance_freq: str = "W",
) -> pd.Series:
    """Daily strategy returns: prior-bar exposure (avoid lookahead) times
    that bar's close-to-close return."""
    df = _prep(price_df)
    exposure = generate_signals(
        df,
        trend_window=trend_window,
        credit_window=credit_window,
        leverage_cap=leverage_cap,
        rebalance_freq=rebalance_freq,
    )
    asset_returns = df["close"].pct_change()
    strat_returns = exposure.shift(1).fillna(0.0) * asset_returns
    return strat_returns.fillna(0.0)
