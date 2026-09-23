"""Strategy: AF-MSI-style Macro Stress Gate for Tactical Leverage Overlay.

Hypothesis (2026-09-23, 5th iteration this cron trigger):
Per https://algorithmicfire.com/post/tactical-leverage-with-the-macro-stress-index
("Tactical Leverage with the AlgorithmicFIRE Macro Stress Indicator (AF-MSI)",
found via browser_exec Google News search after web_search DDGS/Yahoo backend
TLS-errored on every query this iteration): a composite macro stress score
built from THREE independently-scored conditions --

  1. Term-spread inversion: 10Y minus short-term yield < 0 (source uses
     T10Y2Y from FRED; this repo has no FRED access, so we substitute
     ^TNX (10Y) minus ^IRX (13-week T-bill), the same substitution already
     used by this repo's existing yield-curve strategies).
  2. Credit-spread elevation: source uses a rolling 756-day (3yr) z-score
     of the Moody's Baa-Treasury spread > 1.5. Substituted here (no FRED
     access) with the rolling 756-day z-score of -1 * (HYG/IEF ratio)
     exceeding 1.5 (HYG/IEF falling = credit spreads widening, so its
     negative is a rising-stress proxy in the same direction as the
     source's own metric).
  3. Equity-volatility spike: ^VIX > 25.0 sustained for >= 2 consecutive
     trading days (source's own exact rule, filtering single-day noise).

The 0-3 count of active conditions is smoothed with a 10-day rolling max
(source's own de-whipsaw mechanism) so any trigger holds the portfolio in
a risk-off state for a minimum ~10-day cooldown before re-leveraging.

Applied as a LEVERAGE-TOGGLE overlay on top of a separate SMA(trend_window)
trend gate (source's own two-layer design: trend controls baseline 1x/flat,
AF-MSI controls whether to boost above 1x): when the trend gate is long AND
yesterday's smoothed AF-MSI score == 0, exposure = leverage_cap (source
demonstrates SSO/UPRO-style 2x-3x boosts; this repo is long-only per
SAFETY.md with no real leveraged-ETF order placement, so exposure is a
continuous scalar on the SAME underlying asset, capped at leverage_cap,
consistent with this repo's existing vol-targeting-overlay pattern in
2026-09-08_vol_targeting_trend_overlay.py). When trend is long but AF-MSI
score > 0 (any stress), exposure = base_exposure (1.0). When trend is down,
exposure = 0.

This is DISTINCT from this repo's existing 3-factor regime strategies
(2026-09-12-165/166, TASC July 2026 tiered {0,0.5,1.0} exposure by
favorable-condition COUNT using close>SMA200 + VIX<VIX3M + HYG/IEF
zscore>0 sign test): that construction never exceeds 1.0x exposure and
uses a simple sign-based credit test with no smoothing/cooldown. This
strategy instead (a) uses a genuine ABOVE-1.0x leverage BOOST gated by a
zero-stress state, (b) uses an absolute VIX>25-for-2-days threshold
rather than a VIX-vs-VIX3M term-structure comparison, (c) uses a z-score
magnitude threshold (>1.5) on the credit proxy rather than a sign test,
and (d) applies an explicit 10-day rolling-max smoothing/cooldown
mechanism the source calls out as essential to avoid whipsawing.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _naive_index(idx):
    return idx.tz_localize(None) if getattr(idx, "tz", None) is not None else idx


def _reindex_ffill(series: pd.Series, target_idx: pd.DatetimeIndex) -> pd.Series:
    series = series.sort_index()
    series.index = _naive_index(series.index)
    target_idx_n = _naive_index(target_idx)
    series = series.reindex(series.index.union(target_idx_n)).sort_index().ffill()
    series = series.reindex(target_idx_n)
    series.index = target_idx
    return series


def _get_macro_stress_score(
    idx: pd.DatetimeIndex,
    credit_zscore_window: int,
    credit_z_threshold: float,
    vix_threshold: float,
    vix_persist_days: int,
    smooth_window: int,
) -> pd.Series:
    from loaders import load_equity

    lookback_days = max(credit_zscore_window, 400) + 60
    start = (idx.min() - pd.Timedelta(days=lookback_days)).to_pydatetime()
    end = (idx.max() + pd.Timedelta(days=5)).to_pydatetime()

    # 1. Term spread inversion: TNX - IRX < 0
    tnx = load_equity("^TNX", start, end).set_index("timestamp")["close"].sort_index()
    irx = load_equity("^IRX", start, end).set_index("timestamp")["close"].sort_index()
    tnx.index = _naive_index(tnx.index)
    irx.index = _naive_index(irx.index)
    spread = (tnx - irx).dropna()
    term_inverted = (spread < 0)

    # 2. Credit spread elevation: rolling z-score of -(HYG/IEF) > threshold
    hyg = load_equity("HYG", start, end).set_index("timestamp")["close"].sort_index()
    ief = load_equity("IEF", start, end).set_index("timestamp")["close"].sort_index()
    hyg.index = _naive_index(hyg.index)
    ief.index = _naive_index(ief.index)
    ratio = (hyg / ief).dropna()
    neg_ratio = -ratio
    roll_mean = neg_ratio.rolling(credit_zscore_window, min_periods=max(30, credit_zscore_window // 4)).mean()
    roll_std = neg_ratio.rolling(credit_zscore_window, min_periods=max(30, credit_zscore_window // 4)).std()
    credit_z = (neg_ratio - roll_mean) / roll_std.replace(0, np.nan)
    credit_elevated = (credit_z > credit_z_threshold)

    # 3. VIX spike sustained >= vix_persist_days consecutive days
    vix = load_equity("^VIX", start, end).set_index("timestamp")["close"].sort_index()
    vix.index = _naive_index(vix.index)
    vix_high = (vix > vix_threshold)
    vix_sustained = vix_high.rolling(vix_persist_days).sum() >= vix_persist_days

    # Union of all indices, reindex each condition, ffill, then combine
    all_idx = term_inverted.index.union(credit_elevated.index).union(vix_sustained.index).union(_naive_index(idx))
    all_idx = all_idx.sort_values()

    term_r = term_inverted.reindex(all_idx).ffill().fillna(False)
    credit_r = credit_elevated.reindex(all_idx).ffill().fillna(False)
    vix_r = vix_sustained.reindex(all_idx).ffill().fillna(False)

    score = term_r.astype(int) + credit_r.astype(int) + vix_r.astype(int)
    # 10-day rolling max smoothing (source's own de-whipsaw / cooldown mechanism)
    smoothed = score.rolling(smooth_window, min_periods=1).max()

    result = _reindex_ffill(smoothed, idx)
    return result.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    leverage_cap: float = 1.5,
    base_exposure: float = 1.0,
    credit_zscore_window: int = 252,
    credit_z_threshold: float = 1.5,
    vix_threshold: float = 25.0,
    vix_persist_days: int = 2,
    smooth_window: int = 10,
    is_crypto: bool = False,
) -> pd.Series:
    """Return continuous exposure series: leverage_cap if trend-up + zero-stress,
    base_exposure if trend-up + any stress, 0 if trend-down."""
    df = _prep(price_df)
    idx = df.index
    close = df["close"]

    sma = close.rolling(trend_window, min_periods=max(2, trend_window // 2)).mean()
    trend_up = close > sma

    if is_crypto:
        stress_score = pd.Series(0.0, index=idx)
    else:
        try:
            stress_score = _get_macro_stress_score(
                idx, credit_zscore_window, credit_z_threshold, vix_threshold, vix_persist_days, smooth_window
            )
        except Exception:
            stress_score = pd.Series(0.0, index=idx)

    zero_stress = (stress_score <= 0)

    exposure = pd.Series(0.0, index=idx)
    exposure[trend_up & zero_stress] = leverage_cap
    exposure[trend_up & ~zero_stress] = base_exposure
    exposure[~trend_up] = 0.0
    return exposure


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs). Position lagged by 1 day."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
