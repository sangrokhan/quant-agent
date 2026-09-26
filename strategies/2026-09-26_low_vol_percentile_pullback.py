"""Strategy: Low-Volatility Pullback Setup (ATR percentile + SMA(20)/SMA(200)).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-26-017):
Per QuantifiedStrategies.com's FESX (EURO STOXX 50 futures) pullback
setup, disclosed via Facebook posts (Google SERP snippets, full substack
article behind a different unreachable URL): "ATR(14) is in the lowest
25% of the past year" (volatility-compression filter) AND "Close below
the 20-day MA" (short-term pullback within) AND "Close above the 200-day
MA" (long-term uptrend intact) triggers a long entry at "next open".
Adapted here to a long-only equity/crypto implementation: enter at the
NEXT bar's open when ATR(14) is below its own trailing 252-day 25th
percentile AND close<SMA(20) AND close>SMA(200); exit on close crossing
back above SMA(20) (mean-reversion complete) or a max_hold_days safety
time-stop (source's own rule doesn't disclose the exit past "Buy next
open", so a symmetric SMA(20) mean-reversion exit is added per this
repo's convention -- see similar precedent e.g. 2026-09-03_bb_meanrev).

First strategy in this repo to combine a volatility-PERCENTILE-COMPRESSION
filter (not a simple ATR-below-own-MA threshold) with a short-term
pullback (close<SMA(20)) nested inside a long-term uptrend (close>SMA(200))
-- distinct from all prior ATR-percentile-regime and volatility-squeeze
entries, which use different combinations of these conditions or lack the
percentile-rank ATR filter entirely.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    atr_window: int = 14,
    atr_percentile_lookback: int = 252,
    atr_percentile_threshold: float = 0.25,
    short_ma_window: int = 20,
    long_ma_window: int = 200,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    atr = _atr(high, low, close, atr_window)
    atr_pctile_rank = atr.rolling(atr_percentile_lookback).apply(
        lambda x: (x <= x.iloc[-1]).mean() if len(x) > 0 else float("nan"), raw=False
    )
    low_vol = atr_pctile_rank <= atr_percentile_threshold

    short_ma = close.rolling(short_ma_window).mean()
    long_ma = close.rolling(long_ma_window).mean()

    pullback = close < short_ma
    uptrend = close > long_ma

    trigger = low_vol.fillna(False) & pullback & uptrend
    # Source's own rule: "Buy next open" -- shift trigger by 1 bar for entry timing.
    entry = trigger.shift(1).fillna(False)

    exit_signal = close > short_ma

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_signal.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
