"""Strategy: RSI dip-buy with ATR hard stop + recent-high take-profit, trend-gated.

Hypothesis (see knowledge_base/strategies_log.jsonl for the id assigned to
this entry): per Arrow Algo's "Buy the Dip Strategy: Trade Pullbacks With
Rules" (https://arrowalgo.com/buy-the-dip-strategy, read via browser_exec
this iteration), a systematic dip-buy needs three explicit components the
source lays out: (1) a long-term trend filter (close > 200d SMA) so dips are
only bought in an established uptrend, (2) a measurable dip trigger (source
suggests RSI dropping below 30 as one of several valid triggers), and (3) a
pre-defined risk exit: "a hard stop below the level that invalidates the
idea, such as 1.5 ATR beneath the dip low" for the loss side, and "a return
to the recent high" for the profit side (rather than an open-ended
average-down or a vague "feel" exit). This differs from prior single-RSI or
single-CMO oversold-reversal variants in this repo (e.g. 2026-09-04-055 CMO
threshold, 2026-09-03-005 RSI(2)) by combining the RSI entry trigger with the
source's own specific ATR-stop + recent-high-target risk-management pair
instead of a symmetric mean-reversion-to-SMA or fixed time-stop exit only.

Signal logic
------------
- Trend gate: close > SMA(trend_window) (long-only, uptrend precondition).
- Entry: RSI(rsi_period) crosses below rsi_threshold (oversold dip trigger)
  while the trend gate holds.
- On entry, freeze: stop_level = entry-bar low - atr_mult * ATR(atr_period);
  take_profit_level = rolling max close over the prior profit_lookback bars
  (the "recent high" the source's profit exit targets).
- Exit: close <= stop_level (hard stop), OR close >= take_profit_level
  (profit target reached), OR held >= max_hold_days (fallback time-stop,
  since this repo trades close-to-close and can't model true intrabar stop
  fills) OR the trend gate flips false (close <= SMA(trend_window), removes
  the uptrend precondition that justified the dip-buy in the first place).

Interface contract matches strategies/2026-09-03_bb_meanrev_qqq_volregime.py:
generate_signals(price_df, **params) -> pd.Series {0,1}
generate_returns(price_df, **params) -> pd.Series of daily strategy returns
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


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0.0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    return rsi


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    rsi_period: int = 14,
    rsi_threshold: float = 30.0,
    atr_period: int = 14,
    atr_mult: float = 1.5,
    profit_lookback: int = 20,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close, low = df["close"], df["low"]

    sma_trend = close.rolling(trend_window).mean()
    trend_gate = close > sma_trend

    rsi = _rsi(close, rsi_period)
    rsi_prev = rsi.shift(1)
    dip_cross = (rsi_prev >= rsi_threshold) & (rsi < rsi_threshold)

    atr = _atr(df, atr_period)
    recent_high = close.rolling(profit_lookback).max()

    entry_signal = dip_cross & trend_gate.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_level = float("nan")
    tp_level = float("nan")

    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            c = close.iloc[i]
            hit_stop = bool(c <= stop_level) if not math.isnan(stop_level) else False
            hit_tp = bool(c >= tp_level) if not math.isnan(tp_level) else False
            trend_broke = not bool(trend_gate.iloc[i]) if not pd.isna(trend_gate.iloc[i]) else False
            if hit_stop or hit_tp or held >= max_hold_days or trend_broke:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]) and not math.isnan(atr.iloc[i]) and not math.isnan(recent_high.iloc[i]):
                in_position = True
                entry_idx = i
                stop_level = low.iloc[i] - atr_mult * atr.iloc[i]
                tp_level = recent_high.iloc[i]
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
