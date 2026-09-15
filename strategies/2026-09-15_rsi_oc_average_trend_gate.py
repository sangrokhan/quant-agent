"""Strategy: RSI computed on the Open-Close average price (Ehlers,
TASC Feb 2023, via Financial Hacker), 30/70 crossover, gated by an
SMA(trend_window) uptrend filter, long-only.

Hypothesis (knowledge_base id 2026-09-15-114):
Per Financial Hacker (https://financial-hacker.com/open-or-close-why-not-both/),
John Ehlers (TASC Feb 2023) proposed using the average of a bar's open
and close, OC = (Open + Close) / 2, rather than the raw close price, as
the input series for technical indicators -- a simple noise-reduction
technique at the cost of half a bar's additional lag. The source's own
test (plain RSI(OC,14) 30/70 crossover, no trend filter) found "no clear
tendency" -- sometimes better than close-based RSI, sometimes worse,
depending on instrument/period. First open-close-average-input-series
technique in this repo (0 prior matches). This iteration tests it more
rigorously than the source's own quick check: RSI(OC-average, 14)
crossing below 30 (oversold) then back above 30 signals a long entry,
gated by an SMA(trend_window) uptrend filter (this repo's standard
approach for RSI-family mean-reversion-in-an-uptrend strategies, since
un-gated oversold-bounce RSI strategies have repeatedly failed in this
repo's own prior testing), exit on RSI closing above 70 (overbought) or a
max_hold_days time-stop.

Source: https://financial-hacker.com/open-or-close-why-not-both/

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


def _rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, 1e-9)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 14,
    oversold_threshold: float = 30.0,
    overbought_threshold: float = 70.0,
    trend_window: int = 200,
    max_hold_days: int = 20,
) -> pd.Series:
    """Long-only: enter on RSI(OC-average) crossing back above the
    oversold threshold from below, gated by close > SMA(trend_window);
    exit on RSI closing above the overbought threshold, the trend filter
    breaking, or a max_hold_days time-stop.
    """
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"] if "open" in df.columns else close

    oc_avg = (open_ + close) / 2.0
    rsi = _rsi(oc_avg, rsi_period)

    trend_long = close > close.rolling(trend_window).mean()

    was_oversold = rsi.shift(1) < oversold_threshold
    cross_up = was_oversold & (rsi >= oversold_threshold)
    entry_condition = (cross_up & trend_long).fillna(False)
    exit_condition = (rsi > overbought_threshold) | (~trend_long.fillna(False))

    position = pd.Series(0.0, index=close.index)
    entry_vals = entry_condition.to_numpy()
    exit_vals = exit_condition.to_numpy()
    pos = position.to_numpy().copy()
    in_position = False
    bars_held = 0
    for i in range(len(pos)):
        if in_position:
            bars_held += 1
            if exit_vals[i] or bars_held >= max_hold_days:
                in_position = False
                bars_held = 0
                pos[i] = 0.0
            else:
                pos[i] = 1.0
        else:
            if entry_vals[i]:
                in_position = True
                bars_held = 0
                pos[i] = 1.0
            else:
                pos[i] = 0.0
    return pd.Series(pos, index=close.index)


def generate_returns(
    price_df: pd.DataFrame,
    rsi_period: int = 14,
    oversold_threshold: float = 30.0,
    overbought_threshold: float = 70.0,
    trend_window: int = 200,
    max_hold_days: int = 20,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        rsi_period=rsi_period,
        oversold_threshold=oversold_threshold,
        overbought_threshold=overbought_threshold,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret
