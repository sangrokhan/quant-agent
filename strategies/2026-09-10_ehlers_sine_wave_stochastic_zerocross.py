"""Strategy: Ehlers-inspired Sine Wave Stochastic, zero-line-cross confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per https://stonehillforex.com/2026/08/ehlers-sine-wave-stochastic-as-a-confirmation-indicator/
(a stochastic-based variant inspired by John Ehlers' digital-signal-
processing philosophy of treating price as a noisy cyclical signal): the
indicator displays a fast ("green") and slow ("gold") smoothed stochastic
line, computed from a StoPeriod=32/StoSmoothing=5/StoPrice=Close stochastic
(the source's own disclosed default settings). Two confirmation methods are
disclosed: a two-line crossover (earlier, more false signals) and a
zero-line cross of the fast line (more conservative, stronger confirmation,
"the green line has to actually move from one side of the centerline to the
other"). This implementation selects the zero-line-cross variant (source's
own preferred trade-off for confirmation reliability) since the underlying
line-smoothing formula itself isn't fully disclosed in the source (only the
settings and crossover logic are) -- approximated here as a
StoSmoothing-period SMA of the raw %K stochastic (StoPeriod lookback,
StoPrice=Close), recentered around its own 50-midpoint as the zero-line
proxy (i.e. the classic 0-100 stochastic's natural centerline). First
Ehlers-Sine-Wave-family strategy in this repo, distinct from Ehlers
Instantaneous Trendline/Laguerre/Center-of-Gravity already tested (all use
different Ehlers filter constructions, not a stochastic-oscillator base).

Signal logic
------------
- Raw %K[t] = 100 * (close[t] - LowestLow(sto_period)) / (HighestHigh(sto_period) - LowestLow(sto_period))
- Smoothed fast line = SMA(%K, sto_smoothing) (source's disclosed
  StoSmoothing default 5, StoPeriod default 32).
- Entry (long): smoothed fast line crosses above 50 (the natural stochastic
  centerline, this implementation's zero-line proxy) from below.
- Exit: smoothed fast line crosses back below 50, OR a max_hold_days
  time-stop backstop.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    sto_period: int = 32,
    sto_smoothing: int = 5,
    centerline: float = 50.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    lowest_low = close.rolling(sto_period).min()
    highest_high = close.rolling(sto_period).max()
    raw_range = (highest_high - lowest_low).replace(0, float("nan"))
    raw_k = 100.0 * (close - lowest_low) / raw_range

    fast_line = raw_k.rolling(sto_smoothing).mean()

    bull_cross = (fast_line > centerline) & (fast_line.shift(1) <= centerline)
    bear_cross = (fast_line < centerline) & (fast_line.shift(1) >= centerline)

    entry_signal = bull_cross.fillna(False)
    exit_signal = bear_cross.fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_days = 0
    entry_vals = entry_signal.values
    exit_vals = exit_signal.values

    for i in range(len(df)):
        if in_pos:
            hold_days += 1
            exit_now = exit_vals[i] or (hold_days >= max_hold_days)
            if exit_now:
                in_pos = False
                hold_days = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_vals[i]:
                in_pos = True
                hold_days = 0
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    sto_period: int = 32,
    sto_smoothing: int = 5,
    centerline: float = 50.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    pos = generate_signals(
        price_df,
        sto_period=sto_period,
        sto_smoothing=sto_smoothing,
        centerline=centerline,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0)
    return strat_ret
