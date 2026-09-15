"""Strategy: Andreas F. Clenow's "Stocks on the Move" exponential-regression
momentum score, adapted as a single-asset time-series continuous sizing
dial with an SMA(200) market-regime gate and SMA(100)-style stop, since
this repo's harness tests one symbol at a time rather than a
cross-sectionally ranked universe (Clenow's own strategy ranks S&P 500
constituents weekly and holds the top 20%).

Hypothesis (knowledge_base id TBD, this cron trigger):
Per https://teddykoker.com/2019/05/momentum-strategy-from-stocks-on-the-move-in-python/
(Python re-implementation of Andreas F. Clenow's book "Stocks on the Move:
Beating the Market with Hedge Fund Momentum Strategy"): momentum is
measured by fitting an OLS regression of log(close) against a bar index
over a rolling lookback window (default 90 days), then annualizing the
fitted slope and multiplying by the regression's R^2 (goodness-of-fit) to
penalize noisy/choppy trends relative to smooth, high-conviction ones:

    slope, r_value = linregress(arange(n), log(close[-n:]))
    momentum = ((1 + slope) ** 252) * (r_value ** 2)

Clenow's own strategy additionally requires the broad market (S&P 500) to
be above its 200-day moving average before opening new positions, and
exits a position when it drops out of the top-20% cross-sectional
momentum rank OR falls below its own 100-day moving average. This repo's
single-symbol harness cannot replicate the cross-sectional ranking step,
so this adaptation instead uses the momentum SCORE itself (continuously,
via a tanh-squashed sizing dial) as the position-sizing signal, combined
with the same two disclosed absolute filters Clenow uses: the asset's own
SMA(200) regime gate (long-only entries only above it) and an SMA(100)-
style stop (zero out exposure if price falls below trend_window_short).
First strategy in this repo using the OLS-slope-times-R^2 "smooth trend
strength" momentum score (distinct from prior linear-regression-channel
BREAKOUT strategy 2026-09-04-141, which traded band-breakout, not this
score, and distinct from prior information-discreteness/FIP filter
2026-09-10-108, which conditioned on jump discreteness rather than fit
quality).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap]).
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


def _rolling_momentum_score(
    close: pd.Series,
    mom_window: int = 90,
    periods_per_year: int = 252,
) -> pd.Series:
    """Clenow/Koker exponential-regression momentum: OLS slope of log(close)
    vs bar index over a rolling window, annualized and multiplied by R^2.
    Implemented via closed-form OLS (no scipy dependency): slope = Cov(x,y)/
    Var(x); r^2 = Corr(x,y)^2. Uses log-returns' cumulative sum as the
    regressed series (equivalent to regressing log(close) directly, but
    numerically stabler across the rolling window)."""
    log_close = np.log(close)
    n = mom_window
    x = np.arange(n, dtype=float)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()

    def _fit(window: np.ndarray) -> float:
        if np.any(~np.isfinite(window)):
            return np.nan
        y = window
        y_mean = y.mean()
        cov = ((x - x_mean) * (y - y_mean)).sum()
        slope = cov / x_var
        y_var = ((y - y_mean) ** 2).sum()
        if y_var <= 0 or x_var <= 0:
            r2 = 0.0
        else:
            r2 = (cov ** 2) / (x_var * y_var)
        # Annualize the (small, roughly-daily-log-return) slope like the
        # source: ((1+slope)**periods_per_year) * r^2. Guard against
        # negative-base fractional powers (slope <= -1, degenerate).
        base = 1.0 + slope
        if base <= 0:
            return 0.0
        return (base ** periods_per_year) * r2

    momentum = log_close.rolling(n, min_periods=n).apply(_fit, raw=True)
    return momentum


def generate_signals(
    price_df: pd.DataFrame,
    mom_window: int = 90,
    regime_window: int = 200,
    stop_window: int = 100,
    rank_window: int = 252,
    rank_threshold: float = 0.8,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Continuous long-only exposure in [0, leverage_cap]. Clenow's own
    strategy ranks a broad universe of stocks cross-sectionally each week
    and holds only the top 20% by momentum score; this single-symbol
    time-series adaptation instead ranks the asset's OWN momentum score
    against its own trailing ``rank_window``-day history (a rolling
    percentile rank), and scales exposure up continuously once that
    rolling percentile clears ``rank_threshold`` (default 0.8, i.e. "top
    20% of its own recent history" -- a direct time-series analogue of
    Clenow's cross-sectional top-20% cutoff), gated to zero unless price
    is above both its own SMA(regime_window) (Clenow's disclosed "market
    above its 200-day MA" filter, applied here to the traded asset itself
    since this repo has no separate broad-market proxy wired into
    loaders.py per-symbol) and SMA(stop_window) (Clenow's disclosed
    100-day-MA position stop)."""
    df = _prep(price_df)
    close = df["close"]

    momentum = _rolling_momentum_score(close, mom_window=mom_window)
    pct_rank = momentum.rolling(rank_window, min_periods=rank_window).apply(
        lambda w: (w[-1] > w[:-1]).mean() if len(w) > 1 else 0.0, raw=True
    )
    # Rescale [rank_threshold, 1.0] -> [0, 1] continuously; below threshold
    # is flat (0 exposure), matching Clenow's binary top-20%-only holding.
    dial = ((pct_rank - rank_threshold) / (1.0 - rank_threshold)).clip(lower=0.0, upper=1.0)

    sma_regime = close.rolling(regime_window, min_periods=regime_window).mean()
    sma_stop = close.rolling(stop_window, min_periods=stop_window).mean()
    gated = dial.where((close > sma_regime) & (close > sma_stop), 0.0)

    exposure = (gated * leverage_cap).clip(lower=0.0, upper=leverage_cap)
    return exposure.fillna(0.0)


def generate_returns(
    price_df: pd.DataFrame,
    mom_window: int = 90,
    regime_window: int = 200,
    stop_window: int = 100,
    rank_window: int = 252,
    rank_threshold: float = 0.8,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Daily strategy returns: prior-bar exposure (avoid lookahead) times
    that bar's close-to-close return."""
    df = _prep(price_df)
    exposure = generate_signals(
        df,
        mom_window=mom_window,
        regime_window=regime_window,
        stop_window=stop_window,
        rank_window=rank_window,
        rank_threshold=rank_threshold,
        leverage_cap=leverage_cap,
    )
    asset_returns = df["close"].pct_change()
    strat_returns = exposure.shift(1).fillna(0.0) * asset_returns
    return strat_returns.fillna(0.0)
