"""Strategy: Standard Error Bands (SEB) mean-reversion on band-touch-and-reverse.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-113):
Per quantifiedstrategies.com's Standard Error Bands article
(https://www.quantifiedstrategies.com/standard-error-bands/), the SEB
indicator can be interpreted THREE distinct ways: (1) trend-continuation
breakout (already tested & rejected in this repo, id 2026-09-06-126), (2)
pullback-to-centerline during a confirmed uptrend (already tested &
rejected, id 2026-09-08-051), and (3) the source's own third stated
interpretation -- "In situations where the bands form a channel around the
price, the upper and lower bands may signal overbought and oversold
conditions, and the price crossing beyond them and reversing may set up a
mean-reversal trade." This strategy implements ONLY that third, previously
untested MEAN-REVERSION variant: price closes beyond a band (overshoot),
then the very next close moves back inside the band (reversal
confirmation) -> trade back toward the regression centerline. This is
logically distinct from both prior SEB attempts (neither used a
band-touch-then-reverse mean-reversion entry).

Indicator construction (per source)
------------------------------------
- Middle line: `sma_smooth`-period SMA of a `lr_window`-period linear
  regression (least-squares fit) value of price (i.e. the fitted value at
  the last bar of a rolling `lr_window`-bar OLS regression), then smoothed.
- Standard error: rolling standard error of the regression residuals over
  the same `lr_window`.
- Upper/lower bands: `sma_smooth`-period SMA of (regression line +/-
  `se_mult` standard errors).

Signal logic
------------
- Long entry: yesterday's close was <= lower band (oversold overshoot) AND
  today's close crosses back above the lower band (reversal confirmed).
- Exit: close crosses above the middle (regression) line (mean-reversion
  target reached), OR a `max_hold_days` time-stop.
- Flat otherwise. No short side (long-only, matches the rest of this repo's
  strategies and this source's own long-only bias).

Interface contract (validation/grid_test.py, validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} positions)
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


def _rolling_regression_and_se(close: pd.Series, lr_window: int):
    """Rolling OLS fit (value at last point of each window) + std error of residuals."""
    n = len(close)
    fit_vals = np.full(n, np.nan)
    se_vals = np.full(n, np.nan)
    x = np.arange(lr_window, dtype=float)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()

    values = close.values
    for i in range(lr_window - 1, n):
        window = values[i - lr_window + 1 : i + 1]
        if np.isnan(window).any():
            continue
        y_mean = window.mean()
        slope = ((x - x_mean) * (window - y_mean)).sum() / x_var
        intercept = y_mean - slope * x_mean
        fitted = intercept + slope * x
        resid = window - fitted
        se = np.sqrt((resid ** 2).sum() / (lr_window - 2)) if lr_window > 2 else np.std(resid)
        fit_vals[i] = fitted[-1]
        se_vals[i] = se

    return pd.Series(fit_vals, index=close.index), pd.Series(se_vals, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    lr_window: int = 21,
    sma_smooth: int = 3,
    se_mult: float = 2.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    reg_line, se = _rolling_regression_and_se(close, lr_window)
    mid = reg_line.rolling(sma_smooth).mean()
    lower_band = (reg_line - se_mult * se).rolling(sma_smooth).mean()

    below_or_at = close <= lower_band
    below_prev = below_or_at.shift(1).fillna(False)
    entry = below_prev & (close > lower_band)  # reversal: was below, now back above
    exit_meanrev = close > mid

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_meanrev.iloc[i]) or held >= max_hold_days:
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
