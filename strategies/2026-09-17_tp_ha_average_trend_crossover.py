"""Strategy: TypicalPrice/HeikinAshi-Average Trend Crossover with Trend Filter
(Sylvain Vervoort, "Exploring Charting Techniques: Creating A Trading
Strategy, Part 3", TASC Sept 2014 article; code published in TASC's October
2014 Traders' Tips, TradeStation EasyLanguage), read this iteration via
browser_exec at
https://traders.com/Documentation/FEEDbk_docs/2014/10/TradersTips.html
(exact EasyLanguage disclosed directly in the Traders' Tips code section,
after web_search DDGS backend errored on the initial keyword query --
direct traders.com archive URL navigation used instead of a search-engine
fallback since the exact October-2014 URL pattern was already known from
this repo's visited_urls.jsonl ledger of prior TASC months).

Hypothesis (see knowledge_base/strategies_log.jsonl entry for this id):
Comparing an average of the (raw, non-recursively-smoothed) Heikin-Ashi
OHLC average to an average of the standard typical price (H+L+C)/3, with a
persistent state variable that only flips when THREE conditions align on
the same bar (TPAverage>HAAverage, a bullish candle body Close>Open, AND
close above its own 21-day trend SMA -- or the mirror-image bearish triple
for the short/flat side), and exits on the TPAverage/HAAverage average
crossing rather than on the trend filter or candle body alone, gives a
trend-following signal that only re-enters after a confirmed multi-factor
alignment rather than a single-indicator flip. This is distinct from every
prior Heikin-Ashi entry in this repo (e.g. 2026-09-17-114's SVE_haClose
comparison, which uses Vervoort's OWN separately-disclosed further-smoothed
recursive haClose formula and a same-bar-only confirmation with no
persistent-state entry gate) because here the Heikin-Ashi construction is
the simpler, non-doubly-smoothed one Vervoort used earlier in his own
article series, AND entry requires a triple-condition simultaneous
alignment (signal+bar+trend) rather than just signal+bar, AND exit is
gated on the raw crossover rather than on the state machine breaking.
First TypicalPrice/HA-Average trend-crossover-with-trend-filter variant in
this repo.

Exact formula (from TASC Oct 2014 TradeStation EasyLanguage, as read this
iteration; long-only adaptation -- source strategy is long/short symmetric,
this implementation only takes the long side per repo convention):
    haClose = (Open + High + Low + Close) / 4
    haOpen[t] = (haOpen[t-1] + haClose[t-1]) / 2      (seeded haOpen[0]=Open)
    haHigh = max(High, haOpen, haClose)
    haLow  = min(Low, haOpen, haClose)
    HAAverage = SMA((haClose + haOpen + haHigh + haLow) / 4, ha_avg_length)
    TPAverage = SMA(TypicalPrice=(H+L+C)/3, tp_avg_length)
    TrendAverage = SMA(Close, trend_avg_length)

    SignalCondition = TPAverage > HAAverage
    BarCondition = Close > Open
    TrendCondition = Close > TrendAverage

    TrendValue[t] = 1  if SignalCondition and BarCondition and TrendCondition
                  = -1 if (not SignalCondition) and (not BarCondition) and (not TrendCondition)
                  = TrendValue[t-1]  otherwise (persistent state, no else-if match)

    Long entry when TrendValue == 1 (source: "Buy this bar on Close").
    Long exit when TPAverage crosses under HAAverage (source: "Sell this bar
    on Close"), independent of TrendValue's own state.

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


def _heikin_ashi_average(df: pd.DataFrame) -> pd.Series:
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    n = len(df)
    ha_close = (o + h + l + c) / 4.0
    ha_open = np.empty(n, dtype=float)
    for i in range(n):
        if i == 0:
            ha_open[i] = o.iloc[i]
        else:
            ha_open[i] = (ha_open[i - 1] + ha_close.iloc[i - 1]) / 2.0
    ha_open_s = pd.Series(ha_open, index=df.index)
    ha_high = pd.concat([h, ha_open_s, ha_close], axis=1).max(axis=1)
    ha_low = pd.concat([l, ha_open_s, ha_close], axis=1).min(axis=1)
    return (ha_close + ha_open_s + ha_high + ha_low) / 4.0


def generate_signals(
    price_df: pd.DataFrame,
    tp_avg_length: int = 8,
    ha_avg_length: int = 8,
    trend_avg_length: int = 21,
) -> pd.Series:
    """Return a {0,1} long/flat position series per the TASC Oct 2014 rule
    (long-only adaptation)."""
    df = _prep(price_df)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    n = len(df)

    typical_price = (h + l + c) / 3.0
    tp_average = typical_price.rolling(tp_avg_length).mean()

    ha_raw = _heikin_ashi_average(df)
    ha_average = ha_raw.rolling(ha_avg_length).mean()

    trend_average = c.rolling(trend_avg_length).mean()

    signal_condition = tp_average > ha_average
    bar_condition = c > o
    trend_condition = c > trend_average

    bullish_triple = signal_condition & bar_condition & trend_condition
    bearish_triple = (~signal_condition) & (~bar_condition) & (~trend_condition)

    cross_under = (tp_average < ha_average) & (tp_average.shift(1) >= ha_average.shift(1))

    trend_value = np.zeros(n, dtype=int)
    state = 0
    position = np.zeros(n, dtype=int)
    in_long = False

    bullish_vals = bullish_triple.values
    bearish_vals = bearish_triple.values
    cross_under_vals = cross_under.values
    valid_vals = tp_average.notna().values & ha_average.notna().values & trend_average.notna().values

    for i in range(n):
        if not valid_vals[i]:
            position[i] = 0
            continue
        if bullish_vals[i]:
            state = 1
        elif bearish_vals[i]:
            state = -1
        trend_value[i] = state

        if not in_long and state == 1:
            in_long = True
        if in_long and cross_under_vals[i]:
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
