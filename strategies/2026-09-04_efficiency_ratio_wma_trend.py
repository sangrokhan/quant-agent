"""Strategy: Kaufman Efficiency Ratio (ER) trend-strength gate + WMA trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-120):
The Kaufman Efficiency Ratio (ER, aka KER) measures trend "efficiency":
the ratio of the net closing-price change over N periods to the sum of
the absolute bar-to-bar changes over the same N periods (source:
quantifiedstrategies.com). Values near 1.0 = strong, low-noise trend;
values near 0.0 = choppy/noisy market. A CoinQuant strategy snippet
(surfaced via Google SERP) gives a concrete threshold rule: "Enter long
when the Efficiency Ratio(10) rises above 0.30" as a trend-strength gate.
We combine that threshold gate with a WMA trend-direction filter (ER
alone only measures strength, not direction, per the source): long entry
when ER(er_period) > er_threshold AND close > WMA(trend_window); exit
when ER drops back below er_threshold, or close crosses below the WMA,
or a max_hold_days time-stop.

Formula
-------
ER[i] = |close[i] - close[i-N]| / sum(|close[j] - close[j-1]| for j in
         (i-N+1)..i)

Signal logic
------------
- Entry (long): ER(er_period) > er_threshold AND close > WMA(trend_window).
- Exit: ER <= er_threshold, OR close < WMA(trend_window), OR a
  max_hold_days time-stop.
- Flat otherwise.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept params as keyword args.
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _efficiency_ratio(close: pd.Series, period: int) -> pd.Series:
    net_change = (close - close.shift(period)).abs()
    bar_changes = close.diff().abs()
    volatility_sum = bar_changes.rolling(period, min_periods=period).sum()
    er = net_change / volatility_sum.replace(0, float("nan"))
    return er


def _wma(close: pd.Series, window: int) -> pd.Series:
    weights = pd.Series(range(1, window + 1), dtype=float)
    wsum = weights.sum()

    def _wma_calc(x):
        return (x * weights.values).sum() / wsum

    return close.rolling(window, min_periods=window).apply(_wma_calc, raw=True, engine="cython")


def generate_signals(
    price_df: pd.DataFrame,
    er_period: int = 10,
    er_threshold: float = 0.3,
    trend_window: int = 50,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"].astype(float)

    er = _efficiency_ratio(close, er_period)
    wma = _wma(close, trend_window)

    strong_trend = er > er_threshold
    uptrend = close > wma

    entry = (strong_trend & uptrend).fillna(False)
    exit_signal = (~strong_trend | ~uptrend).fillna(True)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
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
    close = df["close"].astype(float)
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
