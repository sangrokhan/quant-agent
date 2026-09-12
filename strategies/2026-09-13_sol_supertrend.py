"""Strategy: SuperTrend (ATR-based) trend following on SOL/USDT and XRP/USDT.

Source: CoinQuant.ai "Supertrend on Solana: 3 Years of Backtest Data Across
Bull, Bear, and Chop" (https://www.coinquant.ai/blog/supertrend-on-solana-3-
years-of-backtest-data-across-bull-bear-and-chop, read via browser_exec this
iteration -- web_search DDGS backend TLS-erroring on every query attempted).
Source's own 2022-2026 SOL/USDT daily backtest: standard SuperTrend
(ATR period=10, multiplier=3) returned +272% (Sharpe 0.83, profit factor
1.74, 41.2% win rate, 46.4% max drawdown) over a period spanning a 90%
bear-market drawdown, an explosive bull run, and long chop -- explicitly
NOT a cherry-picked single good year.

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's
id): plain SuperTrend has already been tested extensively in this repo on
BTC/USDT and ETH/USDT and rejected decisively (2026-09-04-053: accepted
QQQ/SPY, "rejected (crypto, decisively 0/54 grid cells)"; follow-up
attempts to widen the ATR multiplier for crypto whipsaw also failed,
2026-09-11-103). This iteration tests whether the SAME plain SuperTrend
mechanism performs differently on SOL/USDT and XRP/USDT specifically
(first SuperTrend test on either symbol in this repo, following the
altcoin-universe-expansion started in 2026-09-13-027/028) -- the source's
own claim is that SOL's higher volatility and sustained multi-year trend
moves (not caught by BTC/ETH's typically choppier/more-arbitraged price
action) are what make trend-following pay off here, in contrast to
2026-09-13-027/028's finding that MEAN-REVERSION does not generalize to
these altcoins.

Signal logic
------------
- Daily-resampled close/high/low (crypto loader default is hourly).
- atr_period/multiplier: standard SuperTrend construction (source's own
  default: 10/3.0).
- Long while price closes above the SuperTrend line (bullish state); flat
  while below (bearish state) -- long-only, stop-and-reverse-to-flat
  rather than stop-and-reverse-to-short (matching this repo's SAFETY.md
  long-only convention and the existing accepted equity SuperTrend
  strategy's construction).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index.
"""

from __future__ import annotations

import pandas as pd


def _prep_daily(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    daily = df.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    return daily


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def _supertrend(df: pd.DataFrame, atr_period: int, multiplier: float) -> pd.Series:
    """Return a boolean Series: True = bullish (long), False = bearish (flat)."""
    high, low, close = df["high"], df["low"], df["close"]
    atr = _atr(df, atr_period)
    hl2 = (high + low) / 2
    basic_upper = hl2 + multiplier * atr
    basic_lower = hl2 - multiplier * atr

    n = len(df)
    final_upper = basic_upper.copy()
    final_lower = basic_lower.copy()
    trend_up = pd.Series(True, index=df.index)  # bullish state

    for i in range(1, n):
        if close.iloc[i - 1] <= final_upper.iloc[i - 1]:
            final_upper.iloc[i] = min(basic_upper.iloc[i], final_upper.iloc[i - 1])
        else:
            final_upper.iloc[i] = basic_upper.iloc[i]

        if close.iloc[i - 1] >= final_lower.iloc[i - 1]:
            final_lower.iloc[i] = max(basic_lower.iloc[i], final_lower.iloc[i - 1])
        else:
            final_lower.iloc[i] = basic_lower.iloc[i]

        if trend_up.iloc[i - 1] and close.iloc[i] < final_lower.iloc[i]:
            trend_up.iloc[i] = False
        elif (not trend_up.iloc[i - 1]) and close.iloc[i] > final_upper.iloc[i]:
            trend_up.iloc[i] = True
        else:
            trend_up.iloc[i] = trend_up.iloc[i - 1]

    return trend_up


def generate_signals(
    price_df: pd.DataFrame,
    atr_period: int = 10,
    multiplier: float = 3.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series (daily bars)."""
    df = _prep_daily(price_df)
    bullish = _supertrend(df, atr_period, multiplier)
    position = bullish.astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs), daily bars."""
    df = _prep_daily(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
