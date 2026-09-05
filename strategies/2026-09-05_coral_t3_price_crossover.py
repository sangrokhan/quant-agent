"""Strategy: Coral Trend (T3) price-crossover trend strategy.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-090),
sourced from https://in.tradingview.com/scripts/coraltrend/ (TradingView,
"Coral Trend Pullback Strategy (TradeIQ)" description of LazyBear's Coral
Trend indicator): Coral Trend is a color-coded plot of Tim Tillson's T3
moving average (a sextuple-cascaded-EMA construction recombined via a
fixed polynomial of a volume-factor constant, smoother/less-laggy than a
plain EMA of the same period). The TradingView strategy description uses
PRICE CROSSING the Coral Trend line (not the line's own slope) as the
entry/exit trigger, combined with reversal detection of the Coral Trend
direction.

This is a distinct mechanism from the already-tested Coral/T3 strategy in
this repo (2026-09-04-131, "slope_flip" variant: entered when T3's OWN
slope flipped from non-positive to positive, near-missed on QQQ at Sharpe
0.935). Here the entry trigger is instead CLOSE crossing above the T3
line itself (a classic price/moving-average crossover, analogous to how
this repo's other MA-crossover strategies work, but using T3's superior
smoothing/reduced-lag properties instead of a plain EMA/SMA) -- testing
whether the previously-near-missed edge improves when using price-cross
rather than slope-flip as the trigger, since price-cross typically fires
earlier in a genuine trend (right as price reclaims the average) whereas
slope-flip requires the average itself to already be turning.

Signal logic
------------
- T3(close, period, volume_factor): sextuple cascaded EMA with Tillson's
  polynomial recombination (volume_factor=0.7 per the original design and
  most published defaults).
- Long entry: close crosses above T3 (close[t-1] <= T3[t-1], close[t] >
  T3[t]).
- Exit: close crosses back below T3, or after `max_hold_days` (repo
  standard safety time-stop).

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns, position lagged by 1 day to avoid look-ahead bias)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _t3(close: pd.Series, period: int, volume_factor: float) -> pd.Series:
    e1 = close.ewm(span=period, adjust=False, min_periods=period).mean()
    e2 = e1.ewm(span=period, adjust=False, min_periods=period).mean()
    e3 = e2.ewm(span=period, adjust=False, min_periods=period).mean()
    e4 = e3.ewm(span=period, adjust=False, min_periods=period).mean()
    e5 = e4.ewm(span=period, adjust=False, min_periods=period).mean()
    e6 = e5.ewm(span=period, adjust=False, min_periods=period).mean()

    b = volume_factor
    c1 = -(b ** 3)
    c2 = 3 * b ** 2 + 3 * b ** 3
    c3 = -6 * b ** 2 - 3 * b - 3 * b ** 3
    c4 = 1 + 3 * b + b ** 3 + 3 * b ** 2

    t3 = c1 * e6 + c2 * e5 + c3 * e4 + c4 * e3
    return t3


def generate_signals(
    price_df: pd.DataFrame,
    t3_period: int = 10,
    volume_factor: float = 0.7,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    t3 = _t3(close, t3_period, volume_factor)

    crossed_up = (close > t3) & (close.shift(1) <= t3.shift(1))
    crossed_down = (close < t3) & (close.shift(1) >= t3.shift(1))

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    hold_count = 0
    up_arr = crossed_up.fillna(False).values
    down_arr = crossed_down.fillna(False).values

    for i in range(len(df.index)):
        if in_position:
            hold_count += 1
            if down_arr[i] or hold_count >= max_hold_days:
                in_position = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if up_arr[i]:
                in_position = True
                hold_count = 0
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **params)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
