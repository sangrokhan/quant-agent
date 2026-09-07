"""Strategy: David Varadi Oscillator (DVO) mean reversion with trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per the David Varadi Oscillator (DVO), transcribed at
https://www.quantifiedstrategies.com/david-varadi-oscillator/ : the DVO
detrends price by taking an n-period SMA of the ratio (Close / MedianPrice),
where MedianPrice = (High+Low)/2, then computes a rolling percent-rank of
that detrended ratio over a lookback window, scaled 0-100. Varadi's own
stated purpose (per the source) is to strip the trend component out of an
oscillator so it tracks individual price swings more cleanly than RSI-style
oscillators, which "can stay in an overbought/oversold zone for a long time
in a strong trend." The source explicitly analogizes DVO to RSI: "helps
traders identify buy opportunities after pullback swings and sell
opportunities at the end of impulse swings" -- i.e. low DVO = oversold
swing (buy), high DVO = overbought swing (sell). We test the long-only
mean-reversion version: long when DVO crosses below entry_threshold (a
pullback swing extreme), gated by close above a long-term SMA trend filter
(buy dips in an uptrend, matching the source's actual usage guidance: "in
an uptrend, you only look for a buy signal... at key support levels");
exit when DVO recovers above exit_threshold or a max_hold_days time-stop.

First David Varadi Oscillator strategy in this repo -- distinct from
Connors RSI (2026-09-04-113, composite of RSI(3)+streak-RSI(2)+PercentRank
of 1-day ROC) and Cesar Alvarez PercentRank(ROC) (2026-09-04-121,
PercentRank applied directly to a raw ROC(2) value) since DVO's detrending
step is an SMA of the close/median-price RATIO (not ROC, not RSI), before
the percent-rank is taken.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series  (0/1 long/flat)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _dvo(high: pd.Series, low: pd.Series, close: pd.Series, sma_window: int, rank_lookback: int) -> pd.Series:
    median_price = (high + low) / 2.0
    ratio = close / median_price
    detrended = ratio.rolling(sma_window).mean()

    def _pct_rank(window):
        last = window[-1]
        return (window < last).sum() / (len(window) - 1) * 100.0 if len(window) > 1 else 50.0

    dvo = detrended.rolling(rank_lookback).apply(_pct_rank, raw=True)
    return dvo


def generate_signals(
    price_df: pd.DataFrame,
    sma_window: int = 3,
    rank_lookback: int = 252,
    entry_threshold: float = 15.0,
    exit_threshold: float = 70.0,
    trend_window: int = 200,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high, low, close = df["high"], df["low"], df["close"]

    dvo = _dvo(high, low, close, sma_window, rank_lookback)
    trend_sma = close.rolling(trend_window).mean()
    uptrend = close > trend_sma

    entry = (dvo < entry_threshold) & uptrend.fillna(False)
    exit_signal = dvo > exit_threshold

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
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
