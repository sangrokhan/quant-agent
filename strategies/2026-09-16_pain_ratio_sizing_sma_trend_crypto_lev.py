"""Strategy: SMA200 trend-following gate with rolling Pain Ratio (Zephyr,
average-drawdown-based) dynamic exposure scaling -- CRYPTO LEVERAGE-CAP
RECALIBRATION of 2026-09-13-051.

Hypothesis (knowledge_base id TBD, this cron trigger):
2026-09-13-051 (Pain Ratio = annualized return / average-drawdown Pain
Index, dynamic exposure scaling on SMA(trend_window) trend gate) accepted
decisively on SPY and QQQ (Sharpe 1.19/0.89, MDD 11.7%/18.5%, all
validators pass) and even had BTC/USDT Sharpe pass (1.064) and
TC-survival pass (1.046) and walk-forward pass (0.75) -- only MDD failed
decisively at 37.57% > 25% threshold, at leverage_cap left at the default
1.0. This entry applies this repo's established leverage-cap-aware retune
pattern: cut leverage_cap to 0.3 so the Pain-Ratio-driven exposure scaling
signal (already self-limiting via the pain_ratio_reference denominator) is
preserved in shape but its ceiling is capped tightly enough for crypto's
higher realized vol to keep drawdown under 25%. Formula/source unchanged
from 2026-09-13-051 (Becker & Moore, Zephyr Associates 2006;
breakingdownfinance.com, read via browser_exec) -- no new external fetch
needed for this crypto-only recalibration sub-step.

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


def _rolling_pain_ratio(close: pd.Series, window: int) -> pd.Series:
    """Rolling Pain Ratio: annualized mean daily log return / Pain Index
    (average drawdown within the window)."""
    values = close.to_numpy(dtype=float)
    n = len(values)
    out = np.full(n, np.nan)
    if n < window:
        return pd.Series(out, index=close.index)

    price_windows = np.lib.stride_tricks.sliding_window_view(values, window)
    running_peak = np.maximum.accumulate(price_windows, axis=1)
    drawdowns = (running_peak - price_windows) / running_peak
    pain_index = np.nanmean(drawdowns, axis=1)

    log_ret = np.log(close / close.shift(1)).to_numpy(dtype=float)
    ret_windows = np.lib.stride_tricks.sliding_window_view(log_ret, window)
    mean_daily_ret = np.nanmean(ret_windows, axis=1)
    annualized_ret = mean_daily_ret * 252.0

    with np.errstate(divide="ignore", invalid="ignore"):
        pain_ratio = np.where(pain_index > 1e-6, annualized_ret / pain_index, np.nan)

    out[window - 1:] = pain_ratio
    return pd.Series(out, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    pain_window: int = 90,
    pain_ratio_reference: float = 3.0,
    leverage_cap: float = 0.3,
) -> pd.Series:
    """Return a continuous [0, leverage_cap] exposure series."""
    df = _prep(price_df)
    close = df["close"]

    trend_long = close > close.rolling(trend_window).mean()
    pain_ratio = _rolling_pain_ratio(close, pain_window)

    raw_exposure = (pain_ratio / pain_ratio_reference).astype(float)
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
