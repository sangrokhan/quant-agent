"""Strategy: Mass Index RSI oscillator (Donald Dorsey) + SMA200 trend gate.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-037):
Per Donald Dorsey's Mass Index (via
https://www.quantifiedstrategies.com/mass-index-trading-strategy/, source
discloses both the exact formula and its own backtested trading rule):

  range = high - low
  ema9_range = EMA(range, 9)
  ema9_ema9_range = EMA(ema9_range, 9)
  ratio = ema9_range / ema9_ema9_range
  mass_index = rolling_sum(ratio, 25)

The Mass Index itself is non-directional (Dorsey's own "reversal bulge"
rule: value crosses above 27 then back below 26.5 signals *a* reversal,
direction unknown). The source's own backtested, concrete, directional
variant instead takes a short RSI of the Mass Index series itself and
trades its overbought/oversold extremes: "We make a 5-day RSI of the MASS
Index indicator. We buy at the close when the RSI closes below 25. We sell
at the close when the RSI closes above 75." The source's own backtest
(FXI, no trend filter) was weak/erratic: 189 trades, avg gain 0.83%/trade,
max drawdown ~40%, profit factor never exceeded 1.7 across many assets
they tried.

This repo's adaptation: since the source's own bare version already
disclosed a weak/erratic edge, test whether adding a standard SMA200
long-only trend gate (only take the RSI-of-MassIndex<entry_threshold "buy
the dip" signal while price is above its SMA200) rescues it -- consistent
with this repo's general finding that oscillator-only entries usually need
a trend filter to survive transaction costs. Exit on RSI-of-MassIndex
crossing back above exit_threshold, the SMA200 trend flipping bearish, or
a max_hold_days time-stop.

First Mass Index strategy in this repo -- structurally distinct from every
other oscillator tested (RSI, DVO, Connors RSI, TDI, Dynamic-Zone-RSI,
CTI, etc.) since here RSI is computed on a *derived volatility-ratio
indicator* (EMA-of-EMA ratio, summed over 25 bars) rather than directly on
price/close.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(series: pd.Series, window: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _mass_index(high: pd.Series, low: pd.Series, ema_window: int, sum_window: int) -> pd.Series:
    rng = high - low
    ema1 = rng.ewm(span=ema_window, adjust=False).mean()
    ema2 = ema1.ewm(span=ema_window, adjust=False).mean()
    ratio = ema1 / ema2.replace(0.0, pd.NA)
    return ratio.rolling(sum_window).sum()


def generate_signals(
    price_df: pd.DataFrame,
    ema_window: int = 9,
    sum_window: int = 25,
    rsi_window: int = 5,
    entry_threshold: float = 25.0,
    exit_threshold: float = 75.0,
    trend_window: int = 200,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    mi = _mass_index(high, low, ema_window, sum_window)
    mi_rsi = _rsi(mi, rsi_window)

    sma = close.rolling(trend_window).mean()
    above_sma = (close > sma).fillna(False)

    long_entry = (mi_rsi < entry_threshold) & above_sma
    long_exit_signal = mi_rsi > exit_threshold

    n = len(df)
    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            still_trend = bool(above_sma.iloc[i])
            if hold_count >= max_hold_days or bool(long_exit_signal.iloc[i]) or not still_trend:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(long_entry.iloc[i]):
                in_pos = True
                hold_count = 0
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
