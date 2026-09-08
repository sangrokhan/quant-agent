"""Strategy: Parkinson Volatility Compression-to-Expansion Trend Breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per TradingView's "Parkinson Range Oscillator [BackQuant]" script description
(read this iteration; genuinely new indicator family in this repo -- no
prior Parkinson/range-based realized-vol estimator has been tested, unlike
Garman-Klass/Yang-Zhang-adjacent constructs already covered elsewhere):

Parkinson volatility uses the intrabar high-low range (via ln(H/L)) rather
than close-to-close returns, capturing more information about realized
variability per bar:
    logHL2 = ln(high/low)^2
    parkVar = SMA(logHL2, n) / (4*ln(2))
    parkVol = sqrt(parkVar) * 100
Normalized into a z-score oscillator against its own rolling baseline:
    osc = (parkVol - SMA(parkVol, baseline_len)) / STD(parkVol, baseline_len)
Source's own regime-confirming transition rule: an "expansion cross"
(oscillator crossing above its own EMA signal line, confirmed only when
osc > 0, i.e. above-average-vol territory) marks a shift from range
compression into active/informative price movement. Combining this with a
simple trend filter (close > SMA(trend_window)) turns the source's pure
volatility-regime indicator into a testable long-entry signal: enter long
on a Parkinson-vol expansion cross while price is in an established
uptrend (the economic intuition: newly-expanding range/volatility inside
an existing uptrend often marks the trend actually gaining participation,
vs. compression periods which are directionless coiling). Exit on a
compression cross (osc crossing back below its signal line while osc < 0)
or the trend filter breaking.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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


def _parkinson_osc(df: pd.DataFrame, park_window: int, baseline_len: int, signal_len: int):
    high = df["high"]
    low = df["low"]
    log_hl2 = (np.log(high / low)) ** 2
    park_var = log_hl2.rolling(park_window).mean() / (4 * np.log(2))
    park_vol = np.sqrt(park_var) * 100

    park_ma = park_vol.rolling(baseline_len).mean()
    park_sd = park_vol.rolling(baseline_len).std().replace(0.0, np.nan)
    osc = ((park_vol - park_ma) / park_sd).fillna(0.0)
    signal = osc.ewm(span=signal_len, adjust=False).mean()
    return osc, signal


def generate_signals(
    price_df: pd.DataFrame,
    park_window: int = 10,
    baseline_len: int = 100,
    signal_len: int = 14,
    trend_window: int = 50,
) -> pd.Series:
    """Long/flat {0,1} position: long on a Parkinson-vol expansion cross
    (osc crosses above its EMA signal line while osc > 0) confirmed by
    close > SMA(trend_window); exit on a compression cross (osc crosses
    below signal while osc < 0) or the trend filter breaking."""
    df = _prep(price_df)
    close = df["close"]
    osc, signal = _parkinson_osc(df, park_window, baseline_len, signal_len)

    trend_sma = close.rolling(trend_window).mean()
    uptrend = close > trend_sma

    expansion_cross = (osc > signal) & (osc.shift(1) <= signal.shift(1)) & (osc > 0)
    compression_cross = (osc < signal) & (osc.shift(1) >= signal.shift(1)) & (osc < 0)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    for i in range(len(df)):
        trend_ok = bool(uptrend.iloc[i]) if not pd.isna(trend_sma.iloc[i]) else False
        if in_position:
            if bool(compression_cross.iloc[i]) or not trend_ok:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if trend_ok and bool(expansion_cross.iloc[i]):
                in_position = True
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
