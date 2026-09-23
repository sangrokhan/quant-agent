"""Strategy: EMA momentum sequentially conditioned on VIX regime + return skewness.

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD):
Per Alessandro Pontes, "Sequential Conditioning of Momentum on Implied
Volatility Regimes and Distributional Asymmetry" (SSRN abstract_id=6758540,
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6758540, read via
browser_exec this iteration -- web_search DDGS backend RequestError'd on the
discovery query). The abstract frames momentum, implied-volatility regime,
and rolling-return-skewness as three NON-REDUNDANT state variables that
should be conditioned on SEQUENTIALLY (each must independently confirm)
rather than combined into one composite score, grounded in Merton's (1973)
inter-temporal CAPM (state-dependent risk premia) and Lo's (2004) Adaptive
Markets Hypothesis (edge validity is regime-dependent, not constant).

This repo already has isolated pieces of this idea tested separately and
accepted/near-missed in different combinations:
  - EMA/SMA trend-following alone (many prior entries).
  - VIX-level/VIX-vs-SMA regime gates on trend signals (e.g.
    2026-09-05_cvr3_vix_market_timing.py family).
  - Rolling-skewness-as-trend-gate alone (2026-09-08-055/154, positive skew
    matches trend-following payoff profile).
  - CBOE SKEW-index-vs-VIX DIVERGENCE as a crash/risk-off overlay
    (2026-09-23-024/025) -- a different "skew" (index-based, tail-risk
    option pricing) from rolling RETURN skewness used here.

What's genuinely new here: chaining all THREE gates (EMA momentum direction,
VIX-regime calm/turbulent, rolling RETURN skewness sign) as a strict
SEQUENTIAL AND-conjunction on a single instrument, per the source paper's
explicit "sequential architecture" framing -- not a single VIX gate, not a
single skew gate, and not the SKEW-index-vs-VIX divergence construction
already tested.

Signal logic
------------
- Momentum: EMA(fast) > EMA(slow) on close (up-trend condition).
- VIX regime: ^VIX close <= its own rolling SMA(vix_window) -> "calm"
  regime, consistent with Merton's ICAPM state-dependent risk premia (low
  vol regime = momentum more reliably priced).
- Skewness regime: rolling skewness of daily log returns over
  skew_window >= skew_threshold -> positive-skew regime, matching the
  trend-following payoff profile (per prior repo finding, and per Lo's AMH
  framing that edge validity is state-dependent).
- Long only when ALL three conditions hold simultaneously (sequential
  conditioning -- momentum is the primary signal, VIX regime and skewness
  regime act as independent, non-redundant confirming filters); flat
  otherwise.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import sys
import os
import math

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_vix_series(idx: pd.DatetimeIndex) -> pd.Series:
    """Fetch ^VIX daily close and align (ffill) onto the target index.

    Crypto instruments trade 24/7 with no ^VIX equivalent available via
    this repo's yfinance/ccxt-backed loaders; for crypto symbols we fall
    back to treating the VIX-regime gate as always-calm (neutral / passthrough)
    so the strategy remains testable across asset classes per Step 6's
    grid requirement, while equity runs get the real VIX regime signal.
    """
    from loaders import load_equity

    start = idx.min() - pd.Timedelta(days=30)
    end = idx.max() + pd.Timedelta(days=2)
    try:
        df = load_equity("^VIX", start.to_pydatetime(), end.to_pydatetime())
    except Exception:
        return pd.Series(float("nan"), index=idx)
    df = _prep(df)
    close = df["close"]

    by_date = close.copy()
    by_date.index = by_date.index.normalize()
    by_date = by_date[~by_date.index.duplicated(keep="last")]

    target_dates = idx.normalize()
    aligned = by_date.reindex(target_dates).ffill()
    aligned.index = idx
    return aligned


def generate_signals(
    price_df: pd.DataFrame,
    ema_fast: int = 20,
    ema_slow: int = 50,
    vix_window: int = 20,
    skew_window: int = 40,
    skew_threshold: float = 0.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long when EMA(fast) > EMA(slow) AND VIX <= its own rolling SMA(vix_window)
    (or VIX unavailable, e.g. crypto -> gate passes through) AND rolling
    skewness of daily log returns >= skew_threshold.
    """
    df = _prep(price_df)
    close = df["close"]

    ema_f = close.ewm(span=ema_fast, adjust=False).mean()
    ema_s = close.ewm(span=ema_slow, adjust=False).mean()
    momentum_ok = ema_f > ema_s

    vix = _get_vix_series(df.index)
    vix_sma = vix.rolling(vix_window, min_periods=max(2, vix_window // 2)).mean()
    vix_calm = vix <= vix_sma
    # If VIX unavailable for this instrument (e.g. crypto), treat gate as
    # always-open (True) rather than always-closed, so the asset class isn't
    # spuriously zeroed out purely due to a missing macro series.
    vix_calm = vix_calm.where(vix.notna(), True)

    log_ret = close.pct_change().apply(
        lambda r: math.log1p(r) if pd.notna(r) and r > -1 else float("nan")
    )
    rolling_skew = log_ret.rolling(skew_window, min_periods=max(5, skew_window // 2)).skew()
    skew_ok = rolling_skew >= skew_threshold

    position = (
        momentum_ok.fillna(False)
        & vix_calm.fillna(True)
        & skew_ok.fillna(False)
    ).astype(int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    ema_fast: int = 20,
    ema_slow: int = 50,
    vix_window: int = 20,
    skew_window: int = 40,
    skew_threshold: float = 0.0,
) -> pd.Series:
    """Daily strategy returns: position(t-1) * price_return(t) (no lookahead)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        ema_fast=ema_fast,
        ema_slow=ema_slow,
        vix_window=vix_window,
        skew_window=skew_window,
        skew_threshold=skew_threshold,
    )
    price_returns = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(float) * price_returns
    return strat_returns
