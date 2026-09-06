"""Strategy: Standard Error Bands trend-continuation (narrowing-band filter).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-126):
QuantifiedStrategies.com's construction of "Standard Error Bands": the
middle line is a 3-period SMA of a 21-period linear-regression curve of
price; the upper/lower bands are a 3-period SMA of the regression line plus
or minus `se_mult` (default 2) standard errors of the regression. Per that
source's and LightningChart's shared interpretation of the indicator: when
the bands are narrowing while sloping in one direction, the trend is
"healthy" and likely to continue; when the bands widen, the trend is
weakening/likely reversing or turning sideways. This strategy operationalizes
that interpretation directly as a testable rule (the source's own backtest
code/entry-exit rules were paywalled, so this is our own translation of
their stated interpretation into a mechanical signal, not a copy of their
proprietary rule set): long entry when close breaks above the upper band
AND band width (upper - lower) is currently narrower than its own
`width_ma_window`-day rolling average (i.e. we are in Class's "narrowing +
trending" regime, not just a volatility blow-out); exit when close drops
back below the middle regression line, OR band width expands past
`expand_mult` times its rolling average (trend "no longer healthy" per the
source's own stated interpretation), OR a `max_hold_days` time-stop.

This is a new indicator family (linear-regression + standard-error bands,
distinct from Bollinger Bands (SMA + std-dev of price) and from the existing
Linear Regression Channel strategy already tested in this repo (channel of
raw regression residual min/max, not standard-error bands with a smoothed 3
period SMA overlay and an explicit narrowing/widening trend-health filter).

Source: https://www.quantifiedstrategies.com/standard-error-bands/ (read via
browser_exec after web_extract failed with the DDGS search-only-backend
error; web_search itself also failed for this iteration's query with a
network error, so browser_exec was used for the Google search too).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _rolling_linreg_and_se(close: pd.Series, window: int):
    """Rolling OLS fit of close vs. time index over `window` bars (vectorized).

    Returns (fitted_value_at_last_point, standard_error_of_estimate) as two
    aligned Series.
    """
    values = close.values.astype(float)
    n = len(values)
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()
    dof = max(window - 2, 1)

    fitted = np.full(n, np.nan)
    se = np.full(n, np.nan)

    if n >= window:
        # Build a strided view of all windows: shape (n-window+1, window)
        windows = np.lib.stride_tricks.sliding_window_view(values, window)
        y_mean = windows.mean(axis=1)
        slope = ((windows - y_mean[:, None]) * (x - x_mean)).sum(axis=1) / x_var
        intercept = y_mean - slope * x_mean
        y_hat_last = intercept + slope * x[-1]
        y_hat_all = intercept[:, None] + slope[:, None] * x[None, :]
        resid = windows - y_hat_all
        std_err = np.sqrt((resid ** 2).sum(axis=1) / dof)

        fitted[window - 1 :] = y_hat_last
        se[window - 1 :] = std_err

    return pd.Series(fitted, index=close.index), pd.Series(se, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    regression_window: int = 21,
    smooth_window: int = 3,
    se_mult: float = 2.0,
    width_ma_window: int = 20,
    expand_mult: float = 1.2,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fitted, se = _rolling_linreg_and_se(close, regression_window)

    mid_raw = fitted
    upper_raw = fitted + se_mult * se
    lower_raw = fitted - se_mult * se

    mid = mid_raw.rolling(smooth_window).mean()
    upper = upper_raw.rolling(smooth_window).mean()
    lower = lower_raw.rolling(smooth_window).mean()

    band_width = upper - lower
    width_ma = band_width.rolling(width_ma_window).mean()

    narrowing = band_width < width_ma
    expanding_alot = band_width > (width_ma * expand_mult)

    entry = (close > upper) & narrowing.fillna(False)
    exit_mid = close < mid
    exit_expand = expanding_alot.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_mid.iloc[i]) or bool(exit_expand.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
