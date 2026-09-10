"""Strategy: Linear Regression Slope negative-slope pullback, gated by an
SMA uptrend filter, fixed-day-hold exit.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per https://www.quantifiedstrategies.com/linear-regression-slope/: the
Linear Regression Slope (LRS) indicator is the rate-of-change (slope) of a
least-squares regression line fit to closing prices over a short lookback
window (source example: 5 days). The source's own disclosed backtest on
SPY: going long when the slope turns NEGATIVE (a short-term pullback) and
exiting after a fixed N-day hold performed best at N=9 (avg gain
0.39%/trade) -- consistent with short-term mean reversion -- while the
opposite rule (buy when slope turns positive) was decisively worse. However
the source's own unconditional backtest "wasn't particularly good" vs
buy-and-hold. This implementation tests whether gating the source's own
negative-slope pullback entry with an SMA(trend_window) uptrend filter
(only buy dips within an established uptrend, a standard trend-filter
pattern already used successfully elsewhere in this repo, e.g.
2026-09-03_bb_meanrev_qqq_volregime.py) sharpens the weak unconditional
edge the source found. First Linear Regression SLOPE (rate-of-change
momentum oscillator) strategy in this repo -- distinct from Linear
Regression CHANNEL variants (band-based) already tested.

Signal logic
------------
- LRS[t] = slope of the least-squares regression line fit to
  close[t-slope_window+1 : t+1] (standard linear-regression-slope
  construction, in price units per bar).
- Entry (long): LRS crosses from >=0 to <0 (slope just turned negative,
  source's own pullback trigger) AND close > SMA(trend_window) (added
  trend filter, this iteration's novel addition).
- Exit: fixed hold_days trading days after entry (source's own disclosed
  best N=9 exit rule), OR the trend filter breaking intraday-hold (added
  safety exit not in source, to avoid holding a "buy the dip" position
  through a trend reversal).

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


def _rolling_slope(series: pd.Series, window: int) -> pd.Series:
    x = np.arange(window)
    x_mean = x.mean()
    denom = ((x - x_mean) ** 2).sum()

    def _slope(y: pd.Series) -> float:
        y_arr = y.values
        return float(((x - x_mean) * (y_arr - y_arr.mean())).sum() / denom)

    return series.rolling(window).apply(_slope, raw=False)


def generate_signals(
    price_df: pd.DataFrame,
    slope_window: int = 5,
    trend_window: int = 200,
    hold_days: int = 9,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    lrs = _rolling_slope(close, slope_window)
    trend_sma = close.rolling(trend_window).mean()
    trend_ok = close > trend_sma

    slope_turned_negative = (lrs < 0) & (lrs.shift(1) >= 0)
    entry_signal = (slope_turned_negative & trend_ok).fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_counter = 0
    entry_vals = entry_signal.values
    trend_ok_vals = trend_ok.fillna(False).values

    for i in range(len(df)):
        if in_pos:
            hold_counter += 1
            exit_now = (hold_counter >= hold_days) or (not trend_ok_vals[i])
            if exit_now:
                in_pos = False
                hold_counter = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_vals[i]:
                in_pos = True
                hold_counter = 0
                position.iloc[i] = 1

    return position


def generate_returns(
    price_df: pd.DataFrame,
    slope_window: int = 5,
    trend_window: int = 200,
    hold_days: int = 9,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    pos = generate_signals(
        price_df,
        slope_window=slope_window,
        trend_window=trend_window,
        hold_days=hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = daily_ret * pos.shift(1).fillna(0)
    return strat_ret
