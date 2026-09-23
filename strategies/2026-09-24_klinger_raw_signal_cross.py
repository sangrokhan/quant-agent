"""Strategy: Klinger Volume Oscillator (KVO) raw signal-line crossover,
NO trend filter -- crypto-tuned unfiltered variant.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-017):
Per CoinQuant's "Klinger Volume Oscillator Strategy Backtest on Bitcoin:
Does Volume Pressure Beat Buy and Hold?"
(https://www.coinquant.ai/blog/klinger-volume-oscillator-strategy-backtest-on-bitcoin-does-volume-pressure-beat-buy-and-hold):
a bare KVO(fast=34, slow=55) crossing above/below its own 13-period EMA
signal line -- with NO additional trend filter -- backtested on BTCUSDT
daily 2021-08 to 2026-08 beat buy-and-hold on return (+72.39% vs +57.33%),
Sharpe (0.66 vs 0.44) and decisively on max drawdown (28.23% vs 76.63%),
while being in the market only 14.12% of the time (62 trades, 32.3% win
rate, ~3:1 average-win:average-loss payoff ratio). This repo has 2 prior
Klinger entries (2026-09-04-084/085), but BOTH added an EMA(50/100) trend
filter and a min_hold_days gate -- neither tested the bare, trend-filter-free
signal-line cross that this specific source validated directly on crypto.
This iteration isolates that exact unfiltered construction.

Signal logic
------------
- Volume force (Klinger's own definition):
    trend[t] = +1 if typical_price[t] > typical_price[t-1] else -1
    (typical_price = (high+low+close)/3; first bar trend defaults to +1)
    dm[t] = high[t] - low[t]  (daily range, Klinger's "daily measurement")
    cm[t] = cm[t-1] + dm[t] if trend[t] == trend[t-1] else dm[t] + dm[t-1]
    (cumulative measurement resets on trend flips)
    vf[t] = volume[t] * abs(2*(dm[t]/cm[t]) - 1) * trend[t] * 100
- KVO = EMA(fast_span, vf) - EMA(slow_span, vf)
- signal = EMA(signal_span, KVO)
- Entry (long): KVO crosses above signal line.
- Exit: KVO crosses below signal line, OR a max_hold_days time-stop as a
  safety net (source's own system has no explicit time-stop; this repo
  consistently adds one to bound worst-case hold duration).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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


def _klinger_vf(df: pd.DataFrame) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    volume = df["volume"]

    typical = (high + low + close) / 3.0
    trend = np.where(typical.diff().fillna(0.0) >= 0, 1.0, -1.0)
    trend = pd.Series(trend, index=df.index)
    trend.iloc[0] = 1.0

    dm = (high - low).fillna(0.0)

    cm = pd.Series(index=df.index, dtype=float)
    cm.iloc[0] = dm.iloc[0]
    trend_vals = trend.values
    dm_vals = dm.values
    cm_vals = np.zeros(len(df))
    cm_vals[0] = dm_vals[0]
    for i in range(1, len(df)):
        if trend_vals[i] == trend_vals[i - 1]:
            cm_vals[i] = cm_vals[i - 1] + dm_vals[i]
        else:
            cm_vals[i] = dm_vals[i - 1] + dm_vals[i]
    cm = pd.Series(cm_vals, index=df.index).replace(0, np.nan)

    ratio = (2.0 * (dm / cm) - 1.0).abs().fillna(0.0)
    vf = volume * ratio * trend * 100.0
    return vf


def _kvo_signal(df: pd.DataFrame, fast_span: int, slow_span: int, signal_span: int):
    vf = _klinger_vf(df)
    kvo = vf.ewm(span=fast_span, adjust=False, min_periods=fast_span).mean() - \
        vf.ewm(span=slow_span, adjust=False, min_periods=slow_span).mean()
    signal = kvo.ewm(span=signal_span, adjust=False, min_periods=signal_span).mean()
    return kvo, signal


def generate_signals(
    price_df: pd.DataFrame,
    fast_span: int = 34,
    slow_span: int = 55,
    signal_span: int = 13,
    max_hold_days: int = 60,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    kvo, signal = _kvo_signal(df, fast_span, slow_span, signal_span)

    above = kvo > signal
    prev_above = above.shift(1).fillna(False)
    cross_up = above & (~prev_above)

    below = kvo < signal
    prev_below = below.shift(1).fillna(True)
    cross_down = below & (~prev_below)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(cross_down.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]):
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
