"""Strategy: Weekly-trend-filtered daily MACD crossover with price-action
trailing exit (Quantpedia "D1H1 + Trailing Stop" methodology, adapted to
daily/weekly timeframes).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-12-192):
Per Quantpedia's "How to Design a Simple Multi-Timeframe Trend Strategy on
Bitcoin" (https://quantpedia.com/how-to-design-a-simple-multi-timeframe-
trend-strategy-on-bitcoin/, David Mesicek, Nov 2025): starting from a bare
MACD crossover (weak alone, Sharpe 0.33 in source's own hourly BTC test),
the source's own step-by-step improvement adds (1) a higher-timeframe
trend filter per Alexander Elder's Triple Screen principle ("trade only in
the direction of the higher-timeframe trend") and (2) a price-action
trailing exit ("continue holding as long as bars close higher than they
open; exit at the close of the first bar that closes lower than it
opens"), reporting cumulative Sharpe improvement from 0.33 -> 0.80 -> 1.07
as each layer is added (source's own hourly BTC results).

Adapted to this repo's daily-bar data (loaders.py provides daily OHLCV,
not hourly): the higher-timeframe filter uses WEEKLY-resampled MACD
(instead of source's Daily-over-Hourly D1H1), and entries/exits happen on
DAILY bars (instead of source's Hourly). This preserves the source's
literal two-part mechanism (HTF-trend-gated entry + price-action trailing
exit) while shifting both timeframes up one level to match available data
granularity.

This is architecturally distinct from the existing Elder Triple Screen
strategy in this repo (2026-09-04-044,
strategies/2026-09-04_triple_screen_weekly_daily.py) which uses a weekly
MACD-histogram-SLOPE trend filter + a daily STOCHASTIC oversold-recovery
entry + no explicit trailing exit (exit only on weekly tide flip). Here:
(a) the entry trigger is a DAILY MACD line/signal CROSSOVER (not
stochastic), (b) the weekly trend filter uses MACD line vs signal line
(not histogram slope), and (c) the exit is a PRICE-ACTION trailing rule
(first bearish daily candle) rather than only a weekly-tide-flip exit.

Signal logic
------------
- Weekly trend: resample daily close to weekly (W-FRI) bars, compute
  MACD(12,26,9) on the weekly series; weekly uptrend = weekly MACD line >
  weekly signal line. Forward-fill this weekly boolean onto the daily
  index (source's own instruction: only the completed prior week's signal
  is known, i.e. lag by one weekly bar to avoid lookahead).
- Daily entry trigger: daily MACD(12,26,9) line crosses above its own
  signal line (bullish crossover) AND the weekly trend is up.
- Exit (price-action trailing stop, source's own literal rule): once long,
  hold as long as each daily bar closes higher than it opens (a "green"
  bar); exit at the close of the first bar that closes lower than it
  opens (a "red" bar). No fixed profit target or stop-loss beyond this
  price-action rule, matching source's own minimalist design.

Interface contract for validators (see validation/validators.py) and
grid_test (see validation/grid_test.py):
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        {0, 1} position series aligned to price_df.index.
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
        Daily strategy returns (position-weighted, no transaction costs
        applied here).

Tunable params (all keyword args, per RESEARCH_LOOP.md Step 5 contract):
    fast_period   (MACD fast EMA span, default 12, source's literal value).
    slow_period   (MACD slow EMA span, default 26, source's literal value).
    signal_period (MACD signal EMA span, default 9, source's literal value).
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


def _macd(close: pd.Series, fast: int, slow: int, signal: int):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line


def generate_signals(
    price_df: pd.DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]

    # Daily MACD crossover trigger.
    macd_d, signal_d = _macd(close, fast_period, slow_period, signal_period)
    cross_up = (macd_d > signal_d) & (macd_d.shift(1) <= signal_d.shift(1))

    # Weekly trend filter.
    weekly_close = close.resample("W-FRI").last().dropna()
    macd_w, signal_w = _macd(weekly_close, fast_period, slow_period, signal_period)
    weekly_uptrend = (macd_w > signal_w)
    # Lag by one weekly bar (only the completed prior week's signal is known)
    # then forward-fill onto the daily index.
    weekly_uptrend_lagged = weekly_uptrend.shift(1)
    weekly_uptrend_daily = weekly_uptrend_lagged.reindex(close.index, method="ffill").fillna(False)

    entry_signal = (cross_up & weekly_uptrend_daily).fillna(False)

    is_green = close > open_

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    for i in range(len(close)):
        if in_pos:
            if is_green.iloc[i]:
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
                in_pos = False
        else:
            if entry_signal.iloc[i]:
                position.iloc[i] = 1
                in_pos = True
            else:
                position.iloc[i] = 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = generate_signals(
        price_df, fast_period=fast_period, slow_period=slow_period, signal_period=signal_period
    )
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
