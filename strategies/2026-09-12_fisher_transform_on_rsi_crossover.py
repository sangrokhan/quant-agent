"""Strategy: Fisher Transform applied to RSI, signal-line crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per https://www.tradingview.com/script/AEVp3IFi-Fisher-Transform-on-RSI/
(PuzzlerTrades, visited this iteration): the classic Ehlers Fisher Transform
is normally applied directly to price (already tested extensively in this
repo: 2026-09-04-051 raw threshold-cross, 2026-09-05-086 SMA-gated,
2026-09-11-001 slope-reversal). This is a DIFFERENT construction: the RSI
itself (not price) is first computed, then rescaled from [0,100] to [-1,1],
then the standard forward Fisher Transform formula is applied to that
rescaled RSI series, then smoothed. This differs from the already-tested
Vervoort Smoothed-RSI-Inverse-Fisher-Transform (2026-09-11-007/008), which
(a) uses the INVERSE Fisher formula (exp based, saturates to a bounded
[-1,1]-ish range) rather than the forward/log-based Fisher transform used
here, and (b) pre-smooths the RSI itself via a 10-stage rainbow MA + double
EMA + zero-lag correction before transforming, producing a very different
input series. Here we use plain RSI(rsi_period), directly Fisher-transformed
(sharpening its turning points into distinct extreme peaks the same way the
original Fisher Transform sharpens price extremes), then crossed against its
own SMA signal line -- the source's own stated "Signal Line ... crossover
points ... bullish crossover suggests a potential buying opportunity"
mechanical rule.

Signal logic
------------
1. RSI(rsi_period) on close.
2. Rescale RSI to [-1, 1]: x = 2 * (RSI/100) - 1, clipped to [-0.999, 0.999]
   to keep the Fisher log term finite.
3. Fisher = 0.5 * ln((1+x)/(1-x)), then smoothed by a simple moving average
   of window `fisher_smooth` (source's own "additional smoothing" step).
4. Signal = SMA(signal_period) of the smoothed Fisher line.
5. Long entry: Fisher crosses above Signal, gated by close > SMA(trend_window)
   (added trend filter, per the source's own FAQ: "add a trend filter like
   the 200 EMA... only take Fisher signals in the direction of the trend" --
   the source explicitly warns raw crossovers whipsaw in ranging markets).
6. Exit: Fisher crosses back below Signal, the trend filter breaks, or a
   max_hold_days time-stop (avoid indefinite holds).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.fillna(50.0)
    return rsi


def _fisher_of_rsi(close: pd.Series, rsi_period: int, fisher_smooth: int) -> pd.Series:
    rsi = _rsi(close, rsi_period)
    x = 2.0 * (rsi / 100.0) - 1.0
    x = x.clip(-0.999, 0.999)
    fisher_raw = 0.5 * np.log((1.0 + x) / (1.0 - x))
    fisher = fisher_raw.rolling(fisher_smooth, min_periods=fisher_smooth).mean()
    return fisher


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 14,
    fisher_smooth: int = 3,
    signal_period: int = 9,
    trend_window: int = 50,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    fisher = _fisher_of_rsi(close, rsi_period, fisher_smooth)
    signal = fisher.rolling(signal_period, min_periods=signal_period).mean()

    trend_sma = close.rolling(trend_window, min_periods=trend_window).mean()
    uptrend = close > trend_sma

    bullish_cross = (fisher > signal) & (fisher.shift(1) <= signal.shift(1))
    bearish_cross = (fisher < signal) & (fisher.shift(1) >= signal.shift(1))

    in_pos = False
    hold_days = 0
    fisher_v = fisher.to_numpy()
    signal_v = signal.to_numpy()
    uptrend_v = uptrend.to_numpy()
    bull_v = bullish_cross.to_numpy()
    bear_v = bearish_cross.to_numpy()
    pos_arr = np.zeros(len(close), dtype=int)

    for i in range(len(close)):
        if np.isnan(fisher_v[i]) or np.isnan(signal_v[i]) or pd.isna(uptrend_v[i]):
            pos_arr[i] = 0
            continue
        if in_pos:
            hold_days += 1
            if bear_v[i] or (not uptrend_v[i]) or hold_days >= max_hold_days:
                in_pos = False
                hold_days = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if bull_v[i] and uptrend_v[i]:
                in_pos = True
                hold_days = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    return pd.Series(pos_arr, index=close.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    rsi_period: int = 14,
    fisher_smooth: int = 3,
    signal_period: int = 9,
    trend_window: int = 50,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        rsi_period=rsi_period,
        fisher_smooth=fisher_smooth,
        signal_period=signal_period,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )

    daily_returns = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(float) * daily_returns
    return strat_returns
