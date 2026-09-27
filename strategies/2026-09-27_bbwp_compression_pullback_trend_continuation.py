"""Strategy: BBWP Compression-Pullback Trend Continuation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-27-082):
per https://pineify.app/resources/blog/bbwp-indicator-tradingview-pine-script
("BBWP Indicator: Rank Volatility with Bollinger Band Width Percentile",
read via browser_exec), the source's disclosed "Strategy #2: Trend
Continuation After Compression" is:
  - Setup: price above a rising 200-period SMA (uptrend); BBWP (Bollinger
    Band Width Percentile: percentile rank of the current BB width over a
    lookback window, 0-100) drops below 25 during a pullback/pause within
    that uptrend.
  - Entry: in the uptrend, enter when price breaks the recent pullback
    HIGH (a local swing high made during/just before the low-BBWP episode)
    AND BBWP is turning higher again (BBWP rising off its low).
  - Exit (source leaves this open -- "hold the rest only while the trend
    structure remains intact"): here operationalized as close below the
    trend SMA.

This is genuinely distinct from this repo's 3 prior BBWP entries (all
already tested/rejected): 2026-09-07-003 BBWP squeeze-BREAKOUT (fires
directly off an absolute low-BBWP reading breaking a compression RANGE,
no pre-existing trend requirement), the high-BBWP-tail mean-reversion
fade, and the Triple-BB exhaustion-reclaim (fires off HIGH BBWP, opposite
tail). This strategy instead requires an ESTABLISHED PRE-EXISTING TREND
(price already above a long SMA) and treats the BBWP compression purely as
a "pause/pullback within the trend" confirmation signal for a continuation
breakout of the pullback's own local high -- a trend-following pullback
entry, not a squeeze/volatility-breakout entry from a flat/ranging base.

Signal logic
------------
- trend_sma = SMA(trend_window); uptrend = close > trend_sma AND
  trend_sma is itself rising (trend_sma > trend_sma.shift(trend_slope_lookback)).
- bb_width = (upper_band - lower_band) / basis, using a bb_window/bb_std
  Bollinger Band construction.
- bbwp = rolling percentile rank of bb_width over bbwp_lookback bars
  (0-100 scale).
- compression = bbwp <= compression_threshold, evaluated over the last
  pullback_lookback bars (i.e. a compression episode occurred recently).
- pullback_high = rolling max of close over pullback_lookback bars (the
  local swing high made during/around the compression episode).
- Entry (long): uptrend AND a compression episode occurred within the
  last pullback_lookback bars AND close > pullback_high.shift(1) (breaks
  the recent local high) AND bbwp > bbwp.shift(1) (BBWP turning higher).
- Exit: close < trend_sma (trend structure breaks).
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _bbwp(close: pd.Series, bb_window: int, bb_std: float, bbwp_lookback: int) -> pd.Series:
    basis = close.rolling(bb_window).mean()
    std = close.rolling(bb_window).std()
    upper = basis + bb_std * std
    lower = basis - bb_std * std
    bb_width = (upper - lower) / basis.replace(0, pd.NA)

    def _pct_rank(window: pd.Series) -> float:
        if len(window) < 2:
            return 50.0
        current = window.iloc[-1]
        return 100.0 * (window < current).sum() / (len(window) - 1) if len(window) > 1 else 50.0

    bbwp = bb_width.rolling(bbwp_lookback).apply(_pct_rank, raw=False)
    return bbwp


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 200,
    trend_slope_lookback: int = 20,
    bb_window: int = 20,
    bb_std: float = 2.0,
    bbwp_lookback: int = 100,
    compression_threshold: float = 25.0,
    pullback_lookback: int = 15,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    trend_sma = close.rolling(trend_window).mean()
    uptrend = (close > trend_sma) & (trend_sma > trend_sma.shift(trend_slope_lookback))

    bbwp = _bbwp(close, bb_window, bb_std, bbwp_lookback)
    bbwp_turning_up = bbwp > bbwp.shift(1)

    compression_recent = (bbwp <= compression_threshold).rolling(pullback_lookback).max().fillna(0).astype(bool)
    pullback_high = close.rolling(pullback_lookback).max().shift(1)

    entry = (
        uptrend.fillna(False)
        & compression_recent
        & (close > pullback_high).fillna(False)
        & bbwp_turning_up.fillna(False)
    )
    exit_trend_break = (close < trend_sma).fillna(False)

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    for i in range(len(df)):
        if in_pos:
            if exit_trend_break.iloc[i]:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if entry.iloc[i]:
                in_pos = True
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **params) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)
    position = generate_signals(price_df, **params)
    strat_ret = daily_ret * position.shift(1).fillna(0)
    return strat_ret
