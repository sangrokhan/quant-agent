"""Strategy: Rich Method -- Triple-MA-Aligned Channel Breakout with Market
Trend Filter (James and John Rich, "Simplify It", TASC November 2015; code
published in TASC January 2016 Traders' Tips), read this iteration via
browser_exec at
https://traders.com/Documentation/FEEDbk_docs/2016/01/TradersTips.html
(exact TradeStation EasyLanguage indicator/strategy code disclosed directly
in the Traders' Tips section, after web_search DDGS backend errored on
prior queries this run -- direct traders.com archive URL navigation to a
previously-unvisited month, discovered by walking forward from adjacent
known TASC months already in this repo's visited_urls.jsonl ledger).

Hypothesis (see knowledge_base/strategies_log.jsonl entry for this id):
The Rich brothers' method combines THREE independent filters before taking
a channel breakout: (1) a MARKET-WIDE trend filter -- the 2-day rate of
change of a 50-day SMA of a reference market symbol (SPY by default) must
be positive for longs (this repo tests it on the SAME symbol as a
self-referential market-trend proxy, since a cross-symbol lookup isn't
available in the strategy interface contract); (2) a triple-MA ALIGNMENT
filter -- close > 50-day SMA AND 20-day SMA > 50-day SMA AND 50-day SMA >
200-day SMA (a stricter simultaneous three-way ordering than a simple
dual-MA crossover); (3) an 8-day Donchian-like channel breakout (average
of the high/low over `chan_length` days, NOT the raw highest-high/
lowest-low) as the actual entry TRIGGER. This is distinct from every prior
triple-MA-alignment strategy in this repo (which typically use only 2
MAs or a simple stacked-MA filter without a market-trend ROC gate) AND
from the repo's plain Donchian breakout entries (which use MAX/MIN of
high/low, not an AVERAGE of high/low as the channel boundary) because it
combines all three mechanisms simultaneously as the source's own disclosed
rule. First "Rich Method" / average-high-low-channel + triple-MA-alignment
+ market-ROC-trend-filter combination in this repo.

Exact rule set (translated from TASC Jan 2016 TradeStation EasyLanguage,
as read this iteration; MarketTrendSymbol is set to the SAME symbol under
test per this repo's single-symbol strategy interface contract, a
reasonable self-referential proxy for "is the broad market/this symbol's
own longer-term momentum currently rising"):
    UpperChanValue = SMA(High, chan_length)
    LowerChanValue = SMA(Low, chan_length)
    FastMAValue = SMA(Close, fast_ma_length)
    MedMAValue = SMA(Close, med_ma_length)
    SlowMAValue = SMA(Close, slow_ma_length)
    MarketTrendAvg = SMA(Close, market_trend_ma_length)  [same-symbol proxy]
    MarketTrendROC = pct_change(MarketTrendAvg, market_trend_roc_period)
    MarketTrend = 1 if MarketTrendROC>0 else -1 (persistent otherwise)

    Long entry: MarketTrend==1 AND Close>MedMAValue AND FastMAValue>MedMAValue
        AND MedMAValue>SlowMAValue AND Close crosses over UpperChanValue.
    Long exit: Close crosses under LowerChanValue.
    (Short side of the source's long/short symmetric strategy omitted per
    this repo's long-only convention.)

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index.
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


def generate_signals(
    price_df: pd.DataFrame,
    chan_length: int = 8,
    fast_ma_length: int = 20,
    med_ma_length: int = 50,
    slow_ma_length: int = 200,
    market_trend_ma_length: int = 50,
    market_trend_roc_period: int = 2,
) -> pd.Series:
    """Return a {0,1} long/flat position series per the Rich Method rule."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    n = len(df)

    upper_chan = high.rolling(chan_length).mean()
    lower_chan = low.rolling(chan_length).mean()
    fast_ma = close.rolling(fast_ma_length).mean()
    med_ma = close.rolling(med_ma_length).mean()
    slow_ma = close.rolling(slow_ma_length).mean()

    market_trend_avg = close.rolling(market_trend_ma_length).mean()
    market_trend_roc = market_trend_avg.pct_change(market_trend_roc_period)

    # persistent MarketTrend state (only updates on a strict >0/<0 reading,
    # per the source's EasyLanguage if/elseif with no else -- carries
    # forward its previous value otherwise)
    market_trend = np.zeros(n, dtype=int)
    state = 0
    roc_vals = market_trend_roc.values
    for i in range(n):
        if not np.isnan(roc_vals[i]):
            if roc_vals[i] > 0:
                state = 1
            elif roc_vals[i] < 0:
                state = -1
        market_trend[i] = state

    aligned_bullish = (
        (close > med_ma) & (fast_ma > med_ma) & (med_ma > slow_ma)
    )

    cross_over_upper = (close > upper_chan) & (close.shift(1) <= upper_chan.shift(1))
    cross_under_lower = (close < lower_chan) & (close.shift(1) >= lower_chan.shift(1))

    entry_signal = (market_trend == 1) & aligned_bullish.values & cross_over_upper.values
    exit_signal = cross_under_lower.values

    valid = (
        upper_chan.notna().values
        & lower_chan.notna().values
        & fast_ma.notna().values
        & med_ma.notna().values
        & slow_ma.notna().values
        & market_trend_avg.notna().values
    )

    position = np.zeros(n, dtype=int)
    in_long = False
    for i in range(n):
        if not valid[i]:
            position[i] = 0
            continue
        if not in_long and entry_signal[i]:
            in_long = True
        elif in_long and exit_signal[i]:
            in_long = False
        position[i] = 1 if in_long else 0

    return pd.Series(position, index=df.index)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
