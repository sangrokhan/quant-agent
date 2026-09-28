"""Strategy: Fibonacci Fan diagonal trendline breakout, LOW-VOL REGIME GATED
(follow-up fix for near-miss 2026-09-28-040).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-28-041):
The plain Fibonacci Fan breakout strategy (2026-09-28-040,
strategies/2026-09-28_fibonacci_fan_trend_support.py) was rejected on a
full-sample basis (SPY Sharpe 0.872, QQQ Sharpe -0.352) but its own grid
test revealed the edge is real and concentrated in low-volatility regimes:
by_vol_regime breakdown was low 13/48 passed, mid 9/48, high 3/48 passed
(pass rate decays monotonically with volatility), and the single best grid
cell was SPY in the low-vol tercile at Sharpe 1.986. This mirrors this
repo's own established pattern (e.g. 2026-09-03-001's Bollinger
mean-reversion strategy, id in
strategies/2026-09-03_bb_meanrev_qqq_volregime.py) of explicitly excluding
the regime that breaks a strategy rather than trading through it blindly.

This iteration adds an explicit realized-volatility regime filter (current
20-day realized vol <= vol_regime_ratio x its own trailing 252-day median)
as an AND-gate alongside the existing SMA(200) uptrend filter and fan-line
breakout entry, so the strategy only trades the fan breakout during the
regime its own grid data showed genuine promise in.

Signal logic (daily bars, causal/no look-ahead):
1. Trend filter: close > SMA(trend_window) (default 200d).
2. Low-vol regime filter: 20-day realized vol (annualized std of daily log
   returns) <= vol_regime_ratio (default 1.0) x its own trailing 252-day
   median -- same construction as strategies/2026-09-03_bb_meanrev_qqq_volregime.py.
3. Fan lines: identical construction to 2026-09-28_fibonacci_fan_trend_support.py
   (diagonal trendlines from swing-low origin through 23.6/38.2/50/61.8%
   retracement price levels, extrapolated forward in time).
4. Entry (long): close crosses ABOVE the upper fan line (default ratio
   0.5) AND uptrend filter holds AND low-vol regime holds.
5. Exit: close crosses back BELOW the lower fan line (default ratio
   0.382), OR the volatility regime flips to high-vol (risk-off exit,
   matching the reference BB mean-reversion strategy's own exit rule), OR
   a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py) and
validation/grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _fan_lines(
    close: pd.Series,
    swing_lookback: int,
    upper_ratio: float,
    lower_ratio: float,
) -> tuple[pd.Series, pd.Series]:
    """Rolling causal computation of the two fan lines' current-bar price.

    Identical construction to strategies/2026-09-28_fibonacci_fan_trend_support.py.
    """
    n = len(close)
    upper_line = pd.Series(np.nan, index=close.index)
    lower_line = pd.Series(np.nan, index=close.index)
    values = close.values

    for t in range(n):
        start = max(0, t - swing_lookback + 1)
        window = values[start : t + 1]
        if len(window) < 5:
            continue
        idx_low_rel = int(np.argmin(window))
        if idx_low_rel >= len(window) - 2:
            continue
        sub_after_low = window[idx_low_rel:]
        idx_high_rel = idx_low_rel + int(np.argmax(sub_after_low))
        if idx_high_rel == idx_low_rel or idx_high_rel >= len(window) - 1:
            continue

        low_price = window[idx_low_rel]
        high_price = window[idx_high_rel]
        if high_price <= low_price:
            continue

        t_low = start + idx_low_rel
        t_high = start + idx_high_rel
        dt_total = t_high - t_low
        if dt_total <= 0:
            continue

        dt_current = t - t_low
        slope_unit = (high_price - low_price) / dt_total

        upper_line.iloc[t] = low_price + upper_ratio * slope_unit * dt_current
        lower_line.iloc[t] = low_price + lower_ratio * slope_unit * dt_current

    return upper_line, lower_line


def generate_signals(
    price_df: pd.DataFrame,
    swing_lookback: int = 40,
    trend_window: int = 200,
    upper_ratio: float = 0.5,
    lower_ratio: float = 0.382,
    max_hold_days: int = 15,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda r: math.log(r) if r and r > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median_1y = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    low_vol_regime = realized_vol <= (vol_median_1y * vol_regime_ratio)

    upper_line, lower_line = _fan_lines(close, swing_lookback, upper_ratio, lower_ratio)

    prev_close = close.shift(1)
    prev_upper = upper_line.shift(1)
    prev_lower = lower_line.shift(1)

    cross_above_upper = (prev_close <= prev_upper) & (close > upper_line)
    cross_below_lower = (prev_close >= prev_lower) & (close < lower_line)

    entry = (
        cross_above_upper.fillna(False)
        & uptrend.fillna(False)
        & low_vol_regime.fillna(False)
    )
    exit_fan = cross_below_lower.fillna(False)
    exit_regime_flip = ~low_vol_regime.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_fan.iloc[i]) or bool(exit_regime_flip.iloc[i]) or held >= max_hold_days:
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
