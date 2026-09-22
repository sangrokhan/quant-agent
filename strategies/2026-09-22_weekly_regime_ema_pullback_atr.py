"""Strategy: Weekly-regime-gated daily EMA pullback with ATR stop/TP and cooldown.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-22-041):
Per Quantpedia's "From Backtest to Benchmark: Validating New Strategies with
Quantpedia API" (https://quantpedia.com/from-backtest-to-benchmark-validating-
new-strategies-with-quantpedia-api/, read via browser_exec since web_extract's
DDGS backend cannot fetch article bodies), the article's worked example is a
silver-futures strategy built from: "a weekly higher-timeframe regime map, a
daily EMA pullback and momentum filter, ATR-based stop loss and take profit
logic, and an eight-bar cooldown" (source's own description of its Python
port of a Pine Script strategy). The source reports the strategy stays flat
most of the time, uses ~10% equity per trade, and achieved Sharpe 0.92 / MDD
-1.13% on silver futures over 2023-2026 -- a conservative, low-turnover
profile.

This is a genuinely new MECHANICAL COMBINATION for this repo: prior EMA
pullback entries (2026-09-12-144 "20-EMA Pullback Reversal Swing") used a
simple RSI+volume filter with no separate weekly-timeframe regime map, no
ATR-based stop/TP, and no explicit cooldown; prior Elder Impulse HTF-filter
entries (2026-09-04-125) used a fixed 65-period EMA slope, not a genuine
weekly-bar resampled regime map. Adapted here as a single-asset, long-only
daily strategy (no options data / no Pine Script source available, so the
exact silver setup is reconstructed generically):

Signal logic
------------
- Weekly regime: resample close to weekly bars, compute SMA(regime_weeks)
  on the weekly series, forward-filled to daily. Bullish regime when the
  latest completed weekly close > weekly SMA.
- Daily EMA(ema_window) pullback: a fresh long entry trigger fires when
  yesterday's close was below EMA(ema_window) and today's close crosses
  back above it (pullback-to-EMA bounce), while in a bullish weekly regime
  AND a short daily momentum filter (close > close.shift(mom_window)) is
  positive.
- ATR(atr_window)-based hard stop-loss (atr_stop_mult * ATR below entry
  price) and take-profit (atr_tp_mult * ATR above entry price), evaluated
  on daily closes (no intrabar fill assumption).
- Cooldown: after any exit (stop, take-profit, or regime flip), no new
  entry is taken for cooldown_bars trading days.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  (0/1 position series)
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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window).mean()


def _weekly_regime(df: pd.DataFrame, regime_weeks: int) -> pd.Series:
    weekly_close = df["close"].resample("W").last()
    weekly_sma = weekly_close.rolling(regime_weeks).mean()
    bullish_weekly = (weekly_close > weekly_sma).astype(int)
    # forward-fill weekly regime onto daily index, no lookahead: shift by
    # one week-bar equivalent is implicit since resample('W').last() labels
    # the bar with the week-ending date, and reindex+ffill only uses data
    # available up to and including that date.
    daily_regime = bullish_weekly.reindex(df.index, method="ffill").fillna(0).astype(int)
    return daily_regime


def generate_signals(
    price_df: pd.DataFrame,
    ema_window: int = 20,
    regime_weeks: int = 20,
    mom_window: int = 5,
    atr_window: int = 14,
    atr_stop_mult: float = 2.0,
    atr_tp_mult: float = 3.0,
    cooldown_bars: int = 8,
    max_hold_days: int = 40,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    n = len(df)

    ema = close.ewm(span=ema_window, adjust=False).mean()
    atr = _atr(df, atr_window)
    regime = _weekly_regime(df, regime_weeks)
    momentum_ok = (close > close.shift(mom_window)).astype(int)

    prev_below = (close.shift(1) < ema.shift(1)).astype(int)
    now_above = (close > ema).astype(int)
    pullback_bounce = (prev_below & now_above).astype(int)

    entry_trigger = (
        (pullback_bounce == 1) & (regime == 1) & (momentum_ok == 1) & atr.notna()
    )

    positions = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    entry_price = None
    entry_idx = 0
    cooldown_until = -1

    close_vals = close.values
    atr_vals = atr.values
    entry_trigger_vals = entry_trigger.values

    for i in range(n):
        if in_pos:
            stop_price = entry_price - atr_stop_mult * entry_atr
            tp_price = entry_price + atr_tp_mult * entry_atr
            hit_stop = close_vals[i] <= stop_price
            hit_tp = close_vals[i] >= tp_price
            time_stop = (i - entry_idx) >= max_hold_days
            if hit_stop or hit_tp or time_stop:
                in_pos = False
                cooldown_until = i + cooldown_bars
                positions.iloc[i] = 0
                continue
            positions.iloc[i] = 1
        else:
            if i > cooldown_until and entry_trigger_vals[i] and not np.isnan(atr_vals[i]):
                in_pos = True
                entry_price = close_vals[i]
                entry_atr = atr_vals[i]
                entry_idx = i
                positions.iloc[i] = 1
            else:
                positions.iloc[i] = 0

    return positions.fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    ema_window: int = 20,
    regime_weeks: int = 20,
    mom_window: int = 5,
    atr_window: int = 14,
    atr_stop_mult: float = 2.0,
    atr_tp_mult: float = 3.0,
    cooldown_bars: int = 8,
    max_hold_days: int = 40,
) -> pd.Series:
    df = _prep(price_df)
    positions = generate_signals(
        df,
        ema_window=ema_window,
        regime_weeks=regime_weeks,
        mom_window=mom_window,
        atr_window=atr_window,
        atr_stop_mult=atr_stop_mult,
        atr_tp_mult=atr_tp_mult,
        cooldown_bars=cooldown_bars,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = positions.shift(1).fillna(0) * daily_ret
    return strat_ret
