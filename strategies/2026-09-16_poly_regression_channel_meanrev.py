"""Strategy: Polynomial Regression Channel mean-reversion (long only).

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
Per a Google AI-overview summary of TradingView/Medium/PyQuantLab writeups
on polynomial regression channels: fit a degree-N polynomial trend curve
(here N=2, a quadratic, fit causally on a rolling trailing window to avoid
look-ahead -- each bar's channel is refit using only that bar's trailing
`channel_window` observations) to the closing price, then build symmetric
upper/lower bands at `band_std_mult` standard deviations of the residuals
around the fitted curve. Source's own disclosed mean-reversion rule: go
long when price touches or dips slightly below the lower channel boundary
WHILE the channel's slope (the polynomial's linear/first-derivative
component at the current bar) is flat or turning upward (a "buy the dip
only in a non-downtrending channel" filter, avoiding fading into a falling
knife). Exit (take profit) when price reaches back to the channel midline
(the fitted polynomial curve value itself) or the upper band, whichever is
configured; this implementation uses the midline per the source's own
"Take Profit (Mean-Reversion)" rule variant.

First polynomial-regression-channel strategy in this repo (0 prior matches
for "polynomial regression channel" in strategies_index.jsonl) -- distinct
from every existing linear-regression-channel strategy (10+ prior entries,
all a degree-1/straight-line fit) since a quadratic fit captures
curvature/acceleration in the trend that a linear channel cannot, and from
Bollinger-Band mean reversion (which bands a moving AVERAGE, not a fitted
regression curve).

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position series)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def _rolling_poly_channel(
    close: pd.Series, window: int, degree: int = 2
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Causal rolling polynomial regression channel: at each bar t, fit a
    degree-`degree` polynomial to close[t-window+1 : t+1] against a local
    time index [0..window-1], and return (fitted value at t, residual std
    over the window, local slope at t = polynomial derivative at the last
    point). Purely causal -- refit at every bar using only trailing data,
    no look-ahead."""
    values = close.to_numpy()
    n = len(values)
    x = np.arange(window)
    fitted_last = np.full(n, np.nan)
    resid_std = np.full(n, np.nan)
    slope_last = np.full(n, np.nan)

    for i in range(window - 1, n):
        y = values[i - window + 1 : i + 1]
        coeffs = np.polyfit(x, y, degree)
        poly = np.poly1d(coeffs)
        fitted = poly(x)
        resid = y - fitted
        fitted_last[i] = fitted[-1]
        resid_std[i] = resid.std(ddof=1) if window > degree + 1 else np.nan
        deriv = poly.deriv()
        slope_last[i] = deriv(x[-1])

    idx = close.index
    return (
        pd.Series(fitted_last, index=idx),
        pd.Series(resid_std, index=idx),
        pd.Series(slope_last, index=idx),
    )


def generate_signals(
    price_df: pd.DataFrame,
    channel_window: int = 60,
    degree: int = 2,
    band_std_mult: float = 2.0,
    slope_flat_threshold: float = 0.0,
) -> pd.Series:
    """0/1 long-only position series.

    Entry/hold long when: (a) close is at or below the lower channel band
    (fitted_value - band_std_mult * resid_std), AND (b) the channel's
    local slope is >= `slope_flat_threshold` (flat or turning upward --
    avoid buying dips inside a still-falling channel). Exit (flat) when
    close reaches back to the channel midline (fitted value).
    """
    df = _prep(price_df)
    close = df["close"]

    fitted, resid_std, slope = _rolling_poly_channel(close, channel_window, degree=degree)
    lower_band = fitted - band_std_mult * resid_std

    entry_trigger = (close <= lower_band) & (slope >= slope_flat_threshold)
    exit_trigger = close >= fitted

    entry_trigger = entry_trigger.fillna(False).to_numpy()
    exit_trigger = exit_trigger.fillna(False).to_numpy()

    n = len(close)
    position = np.zeros(n)
    in_pos = False
    for i in range(n):
        if in_pos:
            if exit_trigger[i]:
                in_pos = False
            else:
                position[i] = 1.0
        else:
            if entry_trigger[i]:
                in_pos = True
                position[i] = 1.0

    return pd.Series(position, index=close.index)


def generate_returns(
    price_df: pd.DataFrame,
    channel_window: int = 60,
    degree: int = 2,
    band_std_mult: float = 2.0,
    slope_flat_threshold: float = 0.0,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        channel_window=channel_window,
        degree=degree,
        band_std_mult=band_std_mult,
        slope_flat_threshold=slope_flat_threshold,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret
