"""Strategy: Ehlers Ultimate Smoother slope + price-position trend following.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-066):
Per https://financial-hacker.com/ehlers-ultimate-smoother/ (converting John
Ehlers' TASC 3/24 "Ultimate Smoother" EasyLanguage code): the Ultimate
Smoother achieves near-zero-lag price smoothing by subtracting the
high-frequency components of price via a 2nd-order recursive highpass
filter, producing "the best, albeit smoothed, representation of the price
curve" relative to a plain EMA or Ehlers' own earlier SuperSmoother. A
reader comment on the source article itself suggested testing "being long
when [price is] higher than [the smoother] and short when below" as the
natural trend-following operationalization of the indicator.

This strategy combines that price-vs-smoother position rule with a slope
confirmation (smoother itself must be rising) to avoid choppy whipsaws in
a flat smoother -- the same slope+price-position mechanism already
validated for the (structurally distinct) Adaptive Laguerre Filter
(2026-09-05-058, accepted QQQ), but here applied to Ehlers' NEWER (2024)
Ultimate Smoother recursion, which uses a different filter-pole
construction (2nd-order highpass subtraction vs ALF's adaptive-gamma
Laguerre cascade) -- first Ultimate-Smoother-based strategy in this repo.

Ultimate Smoother formula (Ehlers 2024, per financial-hacker.com):
    f = (1.414*pi) / length
    a1 = exp(-f)
    c2 = 2*a1*cos(f)
    c3 = -a1*a1
    c1 = (1 + c2 - c3) / 4
    US[t] = (1-c1)*price[t] + (2*c1-c2)*price[t-1] - (c1+c3)*price[t-2]
            + c2*US[t-1] + c3*US[t-2]

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _ultimate_smoother(price: pd.Series, length: int = 20) -> pd.Series:
    f = (1.414 * math.pi) / length
    a1 = math.exp(-f)
    c2 = 2 * a1 * math.cos(f)
    c3 = -a1 * a1
    c1 = (1 + c2 - c3) / 4.0

    values = price.values
    n = len(values)
    us = [0.0] * n
    for i in range(n):
        if i < 2:
            us[i] = values[i]
            continue
        us[i] = (
            (1 - c1) * values[i]
            + (2 * c1 - c2) * values[i - 1]
            - (c1 + c3) * values[i - 2]
            + c2 * us[i - 1]
            + c3 * us[i - 2]
        )
    return pd.Series(us, index=price.index)


def generate_signals(
    price_df: pd.DataFrame,
    smoother_length: int = 20,
    slope_lookback: int = 3,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry: close is above the Ultimate Smoother AND the smoother's
    slope_lookback-bar slope is positive (both conditions, avoiding
    whipsaws in a flat/declining smoother).
    Exit: either condition breaks, or a max_hold_days time-stop.
    """
    df = _prep(price_df)
    close = df["close"]

    us = _ultimate_smoother(close, length=smoother_length)
    slope = us - us.shift(slope_lookback)

    long_condition = (close > us) & (slope > 0)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    hold_days = 0
    for i in range(len(close)):
        if in_position:
            hold_days += 1
            if not bool(long_condition.iloc[i]) or hold_days >= max_hold_days:
                in_position = False
                hold_days = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(long_condition.iloc[i]):
                in_position = True
                hold_days = 0
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
