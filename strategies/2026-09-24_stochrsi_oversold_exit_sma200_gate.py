"""Strategy: Stochastic RSI oversold-exit entry gated by an SMA(200) trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-016):
Per CoinQuant's "Stochastic RSI on Crypto: What the Backtest Data Actually
Shows" (https://www.coinquant.ai/blog/stochastic-rsi-on-crypto-what-the-backtest-data-actually-shows):
a plain StochRSI(rsi_period=14, stoch_period=14, k=3, d=3) system (long on
%K crossing above 20 out of oversold, exit on %K crossing below 80 out of
overbought) tested on BTCUSDT 2020-2026 had a 59.9% win rate but still
lost money overall (-18.37% return, 65.3% MDD) because it kept buying
oversold dips INSIDE downtrends, where losers ran much longer than the
capped winners. The source's own explicit suggested fix: add a 200-period
moving-average trend filter so entries only fire when price is above its
200-MA (avoid catching falling knives). This repo has 6 prior StochRSI
entries but none combine this exact "oversold-exit entry + SMA(200) trend
gate + overbought-exit exit" construction (prior entries used %K/%D
crossovers-in-zone, Chandelier/VWAP/WVF/Chaikin/Inside-Day confluences, or
a continuous sizing dial -- not this specific fix for the source's own
documented failure mode).

Signal logic
------------
- RSI(rsi_period) on close, then Stochastic(stoch_period) of RSI, then
  %K = SMA(k_smooth) of that stochastic, %D = SMA(d_smooth) of %K.
- Trend filter: close > SMA(trend_window) (source's own suggested fix,
  default 200).
- Entry (long): %K crosses above oversold_level (default 20) from below
  AND trend filter is true.
- Exit: %K crosses below overbought_level (default 80) from above, OR a
  max_hold_days time-stop as a safety net (source's own system has no
  time-stop, but this repo consistently adds one to bound worst-case
  hold duration).

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


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _stoch_rsi_k_d(close: pd.Series, rsi_period: int, stoch_period: int, k_smooth: int, d_smooth: int):
    rsi = _rsi(close, rsi_period)
    lowest = rsi.rolling(stoch_period).min()
    highest = rsi.rolling(stoch_period).max()
    stoch = 100 * (rsi - lowest) / (highest - lowest).replace(0, pd.NA)
    stoch = stoch.fillna(50.0)
    k = stoch.rolling(k_smooth).mean()
    d = k.rolling(d_smooth).mean()
    return k, d


def generate_signals(
    price_df: pd.DataFrame,
    rsi_period: int = 14,
    stoch_period: int = 14,
    k_smooth: int = 3,
    d_smooth: int = 3,
    oversold_level: float = 20.0,
    overbought_level: float = 80.0,
    trend_window: int = 200,
    max_hold_days: int = 30,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    k, _d = _stoch_rsi_k_d(close, rsi_period, stoch_period, k_smooth, d_smooth)
    sma_trend = close.rolling(trend_window).mean()
    trend_ok = close > sma_trend

    above_oversold = k > oversold_level
    prev_above_oversold = above_oversold.shift(1).fillna(False)
    cross_up_oversold = above_oversold & (~prev_above_oversold)

    below_overbought = k < overbought_level
    prev_below_overbought = below_overbought.shift(1).fillna(True)
    cross_down_overbought = below_overbought & (~prev_below_overbought)

    entry = cross_up_oversold & trend_ok.fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(cross_down_overbought.iloc[i]) or held >= max_hold_days:
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
