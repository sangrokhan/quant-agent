"""Strategy: SMA200 trend-following gate with CVaR (Expected Shortfall)
tail-risk-targeting position sizing.

Hypothesis (see knowledge_base/strategies_log.jsonl id for this iteration):
Per Rickenberg 2019 "Tail Risk Targeting: Target VaR and CVaR Strategies"
(GARP white paper, https://www.garp.org/white-paper/tail-risk-targeting,
abstract read via browser_exec this iteration) and the CVaR/Expected
Shortfall computation method from
https://blog.quantinsti.com/cvar-expected-shortfall/ (also read via
browser_exec), dynamic position sizing that targets a constant level of
TAIL risk (CVaR/Expected Shortfall -- the average loss beyond the VaR
quantile) outperforms plain volatility (stddev-based) targeting on
Sharpe/drawdown, because CVaR captures the asymmetric fat-tail downside
risk that a symmetric stddev measure misses.

This repo already has an accepted plain inverse-VOLATILITY-targeting
overlay (2026-09-08-165, stddev-based) and an accepted vol-targeted dual
momentum rotation (2026-09-13-003) -- this iteration isolates whether
swapping the SIZING denominator from realized stddev to rolling historical
CVaR(95%) (a tail-risk measure, not a dispersion measure) on the SAME
SMA200 trend-following entry gate changes performance meaningfully. First
CVaR/Expected-Shortfall-based position-sizing strategy in this repo.

Signal logic
------------
- Base directional signal: long when close > SMA(trend_window), flat
  otherwise (identical trend gate to 2026-09-08-165's accepted baseline,
  isolating the sizing-mechanism variable).
- Rolling historical CVaR(95%) of daily returns over `cvar_window` days:
  VaR_95 = 5th percentile of trailing daily returns (a loss threshold);
  CVaR_95 = mean of all trailing daily returns <= VaR_95 (average loss in
  the worst 5% tail, per the Empirical Approach in the QuantInsti source).
- Position size (continuous, capped at `leverage_cap`x):
      raw_exposure = target_cvar / abs(CVaR_95)      (both as daily
                                                        fractional-loss
                                                        magnitudes)
      exposure = clip(raw_exposure, 0, leverage_cap)
  Only applied while the trend gate is long; flat (0 exposure) otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap], not strictly {0,1} -- validators operate on the
    returns series directly, and grid_test.py's Sharpe/MDD checks don't
    require binary positions).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rolling_cvar95(daily_ret: pd.Series, window: int) -> pd.Series:
    """Rolling historical CVaR at the 95% confidence level (average of the
    worst 5% of daily returns within the trailing window), vectorized via
    numpy striding rather than a python-level rolling.apply (which is
    prohibitively slow on long intraday/crypto histories)."""
    import numpy as np

    values = daily_ret.to_numpy(dtype=float)
    n = len(values)
    out = np.full(n, np.nan)
    if n < window:
        return pd.Series(out, index=daily_ret.index)

    # Build a 2D view of all trailing windows (n - window + 1, window).
    windows = np.lib.stride_tricks.sliding_window_view(values, window)
    # NaNs in a window (warm-up period) propagate to nanquantile/nanmean;
    # use nan-aware ops so warm-up rows simply come out as NaN.
    var_95 = np.nanquantile(windows, 0.05, axis=1)
    mask = windows <= var_95[:, None]
    # Guard rows where the mask happens to select nothing (shouldn't occur
    # with continuous data, but fall back to the VaR value itself).
    sums = np.where(mask, windows, np.nan)
    with np.errstate(invalid="ignore"):
        cvar = np.nanmean(sums, axis=1)
    cvar = np.where(np.isnan(cvar), var_95, cvar)
    out[window - 1:] = cvar
    return pd.Series(out, index=daily_ret.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    cvar_window: int = 60,
    target_cvar: float = 0.02,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()

    daily_ret = close.pct_change()
    cvar95 = _rolling_cvar95(daily_ret, cvar_window)
    cvar_magnitude = cvar95.abs().replace(0, pd.NA)

    raw_exposure = (target_cvar / cvar_magnitude).astype(float)
    exposure = raw_exposure.clip(lower=0.0, upper=leverage_cap).fillna(0.0)

    position = exposure.where(trend_long.fillna(False), other=0.0)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
