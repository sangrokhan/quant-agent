"""Strategy: Larry Connors R3 (relaxed decline-count) + 20d True-Range-Percentile
volatility contraction gate.

Hypothesis (see knowledge_base/strategies_log.jsonl):
Per Ali Casey's StatOasis article "Larry Connors R3 Strategy — Rebuilt for
Index Futures (With a Smarter Filter)"
(https://statoasis.com/overfit/research/larry-connors-r3-strategy-for-index-
futuresrebuilt-for-index-futures-(with-a-smarter-filter)): the classic R3
rule (close>SMA200, RSI(2)<10, RSI(2) declined 3 consecutive days, exit
RSI(2)>70) is too strict for modern markets/instruments (few trades). The
source's own explicit fix: (1) relax the RSI decline condition from "3
consecutive days" to "at least X of the last Y RSI readings declining"
(parameterized), (2) gate entries with a proprietary "Market Regime
Volatility Filter" that the source states worked best based on a 20-day true
range PERCENTILE (volatility contraction/compression before a reversal
tends to work best) rather than an SMA-based directional filter. This repo
already has 4 prior Connors R3 variants (2026-09-06-159, 2026-09-07-021,
2026-09-08-087) using the strict 3-consecutive-day decline + SMA-based exit
or fixed RSI-exit, NONE of which test a volatility-percentile ENTRY gate.
This iteration tests that specific missing piece: relaxed decline-count +
20d-TR-percentile compression gate.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd
import numpy as np


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def _true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _tr_percentile(tr: pd.Series, window: int) -> pd.Series:
    def _pct_of_last(x):
        if len(x) < 2:
            return np.nan
        last = x[-1]
        return 100.0 * (x < last).sum() / (len(x) - 1)

    return tr.rolling(window, min_periods=window).apply(_pct_of_last, raw=True)


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 2,
    entry_rsi_level: float = 15.0,
    exit_rsi_level: float = 70.0,
    decline_window: int = 3,
    min_declines: int = 2,
    sma_trend_window: int = 200,
    tr_pct_window: int = 20,
    vol_percentile_threshold: float = 40.0,
    max_hold_days: int = 10,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]

    rsi = _rsi(close, rsi_window)
    sma_trend = close.rolling(sma_trend_window, min_periods=sma_trend_window).mean()
    tr = _true_range(df)
    tr_pctile = _tr_percentile(tr, tr_pct_window)

    rsi_declining = rsi.diff() < 0
    declines_in_window = rsi_declining.rolling(decline_window, min_periods=decline_window).sum()

    entry_trigger = (
        (close > sma_trend)
        & (rsi < entry_rsi_level)
        & (declines_in_window >= min_declines)
        & (tr_pctile <= vol_percentile_threshold)
    )
    exit_trigger = rsi > exit_rsi_level

    position = pd.Series(0, index=df.index, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(len(df)):
        if not in_pos:
            if bool(entry_trigger.iloc[i]):
                in_pos = True
                hold_count = 0
        else:
            hold_count += 1
            if bool(exit_trigger.iloc[i]) or hold_count >= max_hold_days:
                in_pos = False
        position.iloc[i] = 1 if in_pos else 0

    return position.shift(1).fillna(0).astype(int)


def generate_returns(
    price_df: pd.DataFrame,
    rsi_window: int = 2,
    entry_rsi_level: float = 15.0,
    exit_rsi_level: float = 70.0,
    decline_window: int = 3,
    min_declines: int = 2,
    sma_trend_window: int = 200,
    tr_pct_window: int = 20,
    vol_percentile_threshold: float = 40.0,
    max_hold_days: int = 10,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        rsi_window=rsi_window,
        entry_rsi_level=entry_rsi_level,
        exit_rsi_level=exit_rsi_level,
        decline_window=decline_window,
        min_declines=min_declines,
        sma_trend_window=sma_trend_window,
        tr_pct_window=tr_pct_window,
        vol_percentile_threshold=vol_percentile_threshold,
        max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change().fillna(0.0)
    return position * daily_returns
