"""Strategy: Standard Error Bands trend-continuation via pullback-to-regression-line entry.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-051):
Follow-up/variant of already-rejected 2026-09-06-126 (SEB band-BREAKOUT entry,
Sharpe 0.864 fail, param-sensitivity 0.656 fail, negative QQQ cross-ticker
sanity check). Per theindicatorlab.com's SEB review, the recommended
trend-continuation entry is NOT a band breakout but a PULLBACK to the
regression centerline during an established uptrend: "If price rides the
upper band during a strong uptrend and the regression line slopes up, don't
short the touch. Wait for a pullback to the regression line and buy." This
is a genuinely different entry trigger (mean-reversion-to-centerline within
a confirmed uptrend, not a breakout above the outer band) -- testing whether
-126's rejection was specific to the breakout-entry construction rather than
the SEB indicator family itself.

Signal logic
------------
- Rolling linear regression (OLS) of close over regression_window bars gives
  a fitted centerline value and its standard error (SE) at each bar.
- Uptrend confirmed when the regression slope (centerline[t] -
  centerline[t-1]) is positive over trend_confirm_days consecutive bars.
- Entry (long): uptrend confirmed AND close pulls back to within
  pullback_se_mult standard errors of the regression centerline (i.e.
  |close - centerline| <= pullback_se_mult * SE) after having been above the
  centerline + 1 SE at some point in the last pullback_lookback bars (must
  actually be pulling back from a extended position, not just chopping at
  the line).
- Exit: close falls below the centerline - exit_se_mult*SE (trend break), OR
  after max_hold_days trading days.
- Flat (no position) whenever not in an active long.

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


def _rolling_regression(close: pd.Series, window: int) -> tuple[pd.Series, pd.Series]:
    """Rolling OLS of close on bar index; returns (fitted_value_at_last_bar, std_error)."""
    vals = close.values
    n = len(vals)
    fitted = np.full(n, np.nan)
    se = np.full(n, np.nan)
    x = np.arange(window)
    x_mean = x.mean()
    ss_x = np.sum((x - x_mean) ** 2)

    for end in range(window, n + 1):
        y = vals[end - window : end]
        if np.any(np.isnan(y)):
            continue
        y_mean = y.mean()
        b = np.sum((x - x_mean) * (y - y_mean)) / ss_x
        a = y_mean - b * x_mean
        y_hat = a + b * x
        resid = y - y_hat
        dof = max(window - 2, 1)
        s_err = np.sqrt(np.sum(resid ** 2) / dof)
        fitted[end - 1] = y_hat[-1]
        se[end - 1] = s_err

    return pd.Series(fitted, index=close.index), pd.Series(se, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    regression_window: int = 21,
    trend_confirm_days: int = 5,
    pullback_se_mult: float = 0.5,
    pullback_lookback: int = 10,
    exit_se_mult: float = 1.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    centerline, se = _rolling_regression(close, regression_window)
    slope_up = centerline.diff() > 0
    uptrend = slope_up.rolling(trend_confirm_days).apply(lambda s: bool(s.all()), raw=False).astype(bool)

    dist = (close - centerline).abs()
    near_centerline = dist <= (pullback_se_mult * se)
    was_extended = ((close - centerline) > se).rolling(pullback_lookback, min_periods=1).max().astype(bool)

    entry = uptrend.fillna(False) & near_centerline.fillna(False) & was_extended.fillna(False)
    exit_trend_break = close < (centerline - exit_se_mult * se)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trend_break.iloc[i]) or held >= max_hold_days:
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
