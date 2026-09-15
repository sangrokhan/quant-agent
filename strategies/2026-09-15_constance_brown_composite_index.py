"""Strategy: Constance Brown CMB Composite Index MA-crossover, long-only.

Hypothesis (knowledge_base id 2026-09-15-112):
Per StockCharts ChartSchool
(https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/cmb-composite-index),
Constance Brown's CMB Composite Index adds a momentum component to RSI and
deliberately removes RSI's [0,100] boundedness:

    RSI_Chg = 9-period ROC of 14-period RSI
    RSI_Mom = 3-period SMA of 3-period RSI
    Composite Index Line = RSI_Chg + RSI_Mom

Composite Index is plotted with a fast (13-period) and slow (33-period)
SMA of itself. Source's own disclosed rule: the Composite Index Line
crossing above BOTH its MAs is a buy signal; crossing below both is a
sell signal. First Constance Brown Composite Index entry in this repo (0
prior matches) -- distinct from this repo's many existing bounded-RSI
strategies since the Composite Index is deliberately UNBOUND (an RSI
rate-of-change + short-RSI-momentum blend), tested here per the source's
own MA-crossover rule rather than as a continuous sizing dial.

Source: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/cmb-composite-index

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, 1e-9)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def _composite_index(
    close: pd.Series,
    rsi_period: int,
    roc_period: int,
    mom_rsi_period: int,
    mom_sma_period: int,
) -> pd.Series:
    rsi_main = _rsi(close, rsi_period)
    rsi_chg = rsi_main.diff(roc_period)  # simple ROC-as-difference (Brown's own construction is a difference, not %change, of an already-bounded oscillator)

    rsi_short = _rsi(close, mom_rsi_period)
    rsi_mom = rsi_short.rolling(mom_sma_period).mean()

    composite = rsi_chg + rsi_mom
    return composite


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 14,
    roc_period: int = 9,
    mom_rsi_period: int = 3,
    mom_sma_period: int = 3,
    fast_ma_period: int = 13,
    slow_ma_period: int = 33,
    max_hold_days: int = 60,
) -> pd.Series:
    """Long-only: enter when the Composite Index Line crosses above BOTH
    its fast and slow SMAs (source's own disclosed rule); exit when it
    crosses back below either, or after max_hold_days.
    """
    df = _prep(price_df)
    close = df["close"]

    composite = _composite_index(close, rsi_period, roc_period, mom_rsi_period, mom_sma_period)
    fast_ma = composite.rolling(fast_ma_period).mean()
    slow_ma = composite.rolling(slow_ma_period).mean()

    long_condition = (composite > fast_ma) & (composite > slow_ma)
    long_condition = long_condition.fillna(False)

    position = pd.Series(0.0, index=close.index)
    vals = long_condition.to_numpy()
    pos = position.to_numpy().copy()
    in_position = False
    bars_held = 0
    for i in range(len(vals)):
        if in_position:
            bars_held += 1
            if not vals[i] or bars_held >= max_hold_days:
                in_position = False
                bars_held = 0
                pos[i] = 0.0
            else:
                pos[i] = 1.0
        else:
            if vals[i]:
                in_position = True
                bars_held = 0
                pos[i] = 1.0
            else:
                pos[i] = 0.0
    return pd.Series(pos, index=close.index)


def generate_returns(
    price_df: pd.DataFrame,
    rsi_period: int = 14,
    roc_period: int = 9,
    mom_rsi_period: int = 3,
    mom_sma_period: int = 3,
    fast_ma_period: int = 13,
    slow_ma_period: int = 33,
    max_hold_days: int = 60,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        rsi_period=rsi_period,
        roc_period=roc_period,
        mom_rsi_period=mom_rsi_period,
        mom_sma_period=mom_sma_period,
        fast_ma_period=fast_ma_period,
        slow_ma_period=slow_ma_period,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret
