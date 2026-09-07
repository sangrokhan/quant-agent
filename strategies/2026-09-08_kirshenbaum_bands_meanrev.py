"""Strategy: Kirshenbaum Bands mean reversion, uptrend-filtered.

Hypothesis (knowledge_base id=2026-09-08-021):
Kirshenbaum Bands, authored by Paul Kirshenbaum (per
https://docs.motivewave.com/studies/k-l and
https://www.tradingview.com/script/dBTwZawK-Kirshenbaum-Bands/), place an
EMA centerline with bands offset by `noSdDev` standard errors of a rolling
linear-regression fit of price (not a plain rolling stdev like Bollinger
Bands) -- this measures volatility "around the current trend" rather than
raw dispersion. When close dips below the lower Kirshenbaum band while the
longer-term trend (SMA200) is still up, that is a short-term overextension
against the prevailing trend that should mean-revert back to the EMA
centerline. This repo has already tested and rejected a related-but-distinct
"Standard Error Bands" trend-CONTINUATION strategy (2026-09-06-126: SMA of a
linreg line +/- SE bands, trading breakouts ABOVE the band, no EMA
centerline, no uptrend filter) and a raw OLS "Linear Regression Channel"
breakout (2026-09-04-141). Kirshenbaum Bands differ mechanically on three
counts: (1) centerline is an EMA of price, not an SMA of the regression
line itself; (2) band half-width is the *standard error* of a separate
rolling linear-regression fit (regression period2), decoupled from the EMA
period1; (3) here we trade mean-REVERSION off the LOWER band with a trend
filter, the opposite side/direction from both prior regression-band tests.

Signal logic
------------
- EMA(period1) of close = centerline.
- Rolling OLS linear regression of close over the trailing `period2` bars;
  standard error = sqrt(sum(residual^2) / (period2 - 2)).
- Lower band = EMA(period1) - noSdDev * stdErr(period2).
- Upper trend filter: close > SMA(trend_window) (only take the reversion
  trade when the longer-term trend is still up, consistent with this repo's
  prior finding, e.g. 2026-09-03-001, that unconditional mean reversion
  underperforms across regimes/trend states).
- Entry (long): close crosses below the lower Kirshenbaum band AND
  close > SMA(trend_window).
- Exit: close crosses back above the EMA centerline (mean-reversion target
  reached), OR held >= max_hold_days (avoid indefinite holds), OR the trend
  filter breaks (close <= SMA(trend_window), risk-off exit).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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


def _rolling_stderr(close: pd.Series, period2: int) -> pd.Series:
    """Standard error of a rolling OLS linear-regression fit of `close`
    against a bar-index x-axis, over a trailing window of length period2."""
    x = np.arange(period2, dtype=float)
    x_mean = x.mean()
    ss_x = ((x - x_mean) ** 2).sum()

    def _se(window: np.ndarray) -> float:
        y = window
        y_mean = y.mean()
        slope = ((x - x_mean) * (y - y_mean)).sum() / ss_x
        intercept = y_mean - slope * x_mean
        fitted = intercept + slope * x
        resid = y - fitted
        if period2 <= 2:
            return np.nan
        return float(np.sqrt((resid ** 2).sum() / (period2 - 2)))

    return close.rolling(period2).apply(_se, raw=True)


def generate_signals(
    price_df: pd.DataFrame,
    period1: int = 30,
    period2: int = 20,
    no_sd_dev: float = 1.0,
    trend_window: int = 200,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ema = close.ewm(span=period1, adjust=False).mean()
    stderr = _rolling_stderr(close, period2)
    lower_band = ema - no_sd_dev * stderr

    trend_sma = close.rolling(trend_window, min_periods=trend_window // 2).mean()
    uptrend = close > trend_sma

    entry = (close < lower_band) & uptrend.fillna(False)
    exit_meanrev = close > ema
    exit_trend_break = ~uptrend.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
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
