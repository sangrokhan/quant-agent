"""Strategy: Dorsey Inertia (RVI smoothed via rolling linear regression), midline crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-12-151):
Per Donald Dorsey, "Refining the Relative Volatility Index" (Stocks &
Commodities, Sep 1995), as summarized/confirmed by
https://www.tradingview.com/script/bzxmXFGd-Dorsey-Inertia/ ("Inertia is
based on Relative Volatility Index (RVI) smoothed using linear
regression... When the indicator is below 50, it signals bearish market
sentiment and when the indicator is above 50 it signals a bullish trend")
and https://stonehillforex.com/dorsey-inertia-as-a-confirmation-indicator/
(exact mechanical rule: "Long: Signal line crosses above the midline (50).
Short: Signal line crosses below the midline (50)." with default settings
RVIPeriod=10 [lookback for the RVI up/down std-dev smoothing], AvgPeriod=14
[std-dev length applied within RVI], SmoothingPeriod=20 [linear-regression
"inertia" smoothing length applied to the raw RVI series]).

This is architecturally distinct from the already-tested plain Dorsey RVI
(2026-09-05-003: raw RVI, asymmetric buy>50/exit<40 threshold) because here
the RVI itself is first smoothed by a rolling linear-regression fit before
the symmetric 50-midline crossover rule is applied -- the "inertia" smoothing
step is the entire point of Dorsey's own follow-up refinement and changes
both the entry timing and the whipsaw profile relative to trading the raw
RVI directly.

Formula:
    up_std[t]  = rolling_std(close, avg_period)[t] if close[t] > close[t-1] else 0
    down_std[t] = rolling_std(close, avg_period)[t] if close[t] < close[t-1] else 0
    upper = rolling_mean(up_std, rvi_period)
    lower = rolling_mean(down_std, rvi_period)
    rvi = 100 * upper / (upper + lower)
    inertia = rolling_linreg_fit(rvi, smoothing_period)   # value of the
        least-squares regression line at the last bar of each window

Signal logic:
    Entry (long): inertia crosses above 50 (inertia[t-1] <= 50 < inertia[t]).
    Exit: inertia crosses back below 50, or a max_hold_days time-stop.

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
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


def _rolling_linreg(series: pd.Series, window: int) -> pd.Series:
    """Rolling least-squares regression line value at the LAST bar of each
    window (the fitted value at t, using bars [t-window+1, t])."""
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()

    def _fit_last(vals: np.ndarray) -> float:
        y = vals
        y_mean = y.mean()
        slope = ((x - x_mean) * (y - y_mean)).sum() / x_var
        intercept = y_mean - slope * x_mean
        return intercept + slope * x[-1]

    return series.rolling(window).apply(_fit_last, raw=True)


def _dorsey_rvi(close: pd.Series, rvi_period: int, avg_period: int) -> pd.Series:
    std = close.rolling(avg_period).std()
    up_move = close > close.shift(1)
    down_move = close < close.shift(1)
    up_std = std.where(up_move, 0.0)
    down_std = std.where(down_move, 0.0)
    upper = up_std.rolling(rvi_period).mean()
    lower = down_std.rolling(rvi_period).mean()
    denom = upper + lower
    rvi = 100.0 * upper / denom.replace(0.0, np.nan)
    return rvi


def generate_signals(
    price_df: pd.DataFrame,
    rvi_period: int = 10,
    avg_period: int = 14,
    smoothing_period: int = 20,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rvi = _dorsey_rvi(close, rvi_period, avg_period)
    inertia = _rolling_linreg(rvi, smoothing_period)

    entry = (inertia > 50) & (inertia.shift(1) <= 50)
    exit_cross = (inertia < 50) & (inertia.shift(1) >= 50)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_cross.iloc[i]) or held >= max_hold_days:
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
