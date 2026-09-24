"""Strategy: Pring's Special K, price-trend-confirmed 10-day-MA crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-XXX):
Per https://chartschool.stockcharts.com/.../prings-special-k (browser_exec;
web_extract failed -- ddgs search-only backend) and
https://iqoptionwiki.com/martin-prings-special-k-indicator/ (browser_exec):
Special K is a weighted sum of 12 smoothed rate-of-change terms combining
short/intermediate/long-term momentum cycles into one series:

    Special K = SMA(10, ROC(10))  * 1 + SMA(10, ROC(15))  * 2
              + SMA(10, ROC(20))  * 3 + SMA(15, ROC(30))  * 4
              + SMA(50, ROC(40))  * 1 + SMA(65, ROC(65))  * 2
              + SMA(75, ROC(75))  * 3 + SMA(100,ROC(100)) * 4
              + SMA(130,ROC(195)) * 1 + SMA(130,ROC(265)) * 2
              + SMA(130,ROC(390)) * 3 + SMA(195,ROC(530)) * 4

Per StockCharts' own suggested-scan rules: a bullish short-term cross is
"Special K > its 10-day SMA" newly crossing up; per IQOptionWiki's
price-confirmed variant: go long when price crosses above its EMA100 AND
Special K crosses above its own zero line (both conditions act as a primary
-trend filter). This strategy combines both sources: Special K crossing
above its 10-day SMA (short-term timing signal, StockCharts) is only acted
on when price is already above its EMA100 (primary trend filter,
IQOptionWiki) -- i.e. only take pro-trend signals, matching StockCharts'
own stated preference ("trades executed in the direction of the main trend
are more likely to be successful"). First Special K strategy in this repo
(0 prior index hits) -- distinct from the repo's 11 prior Know Sure Thing
(KST) entries, which is Pring's other, differently-weighted ROC-summation
indicator.

NOTE: StockCharts states >=725 data points needed to fully form the
longest (530-period ROC + 195-period SMA) component; this repo's loaders
provide ~7.5 years (~1885 daily bars) of QQQ/SPY history, comfortably above
that floor.

Signal logic
------------
- Special K as above (12-term weighted ROC-SMA sum).
- signal_line = SMA(10, Special K).
- primary_trend_up = close > EMA(100, close).
- Entry (long): Special K crosses above signal_line AND primary_trend_up.
- Exit: Special K crosses below signal_line, OR primary_trend_up turns
  False, OR after max_hold_days.
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _roc(close: pd.Series, period: int) -> pd.Series:
    return (close / close.shift(period) - 1.0) * 100.0


def _special_k(close: pd.Series) -> pd.Series:
    terms = [
        (10, 10, 1), (15, 10, 2), (20, 10, 3), (30, 15, 4),
        (40, 50, 1), (65, 65, 2), (75, 75, 3), (100, 100, 4),
        (195, 130, 1), (265, 130, 2), (390, 130, 3), (530, 195, 4),
    ]
    total = pd.Series(0.0, index=close.index)
    for roc_period, sma_period, weight in terms:
        roc = _roc(close, roc_period)
        smoothed = roc.rolling(sma_period).mean()
        total = total + smoothed * weight
    return total


def generate_signals(
    price_df: pd.DataFrame,
    signal_sma: int = 10,
    trend_ema: int = 100,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    special_k = _special_k(close)
    signal_line = special_k.rolling(signal_sma).mean()
    ema_trend = close.ewm(span=trend_ema, adjust=False).mean()
    primary_trend_up = close > ema_trend

    cross_up = (special_k > signal_line) & (special_k.shift(1) <= signal_line.shift(1))
    cross_down = (special_k < signal_line) & (special_k.shift(1) >= signal_line.shift(1))

    entry = (cross_up & primary_trend_up).to_numpy()
    exit_pattern = (cross_down | (~primary_trend_up)).to_numpy()

    position = pd.Series(0, index=close.index, dtype=int)
    pos_arr = position.to_numpy().copy()

    in_position = False
    hold_days = 0
    for i in range(len(close)):
        if in_position:
            hold_days += 1
            if exit_pattern[i] or hold_days >= max_hold_days:
                in_position = False
                hold_days = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if entry[i]:
                in_position = True
                hold_days = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    position = pd.Series(pos_arr, index=close.index, dtype=int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    signal_sma: int = 10,
    trend_ema: int = 100,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df, signal_sma=signal_sma, trend_ema=trend_ema, max_hold_days=max_hold_days
    )
    daily_ret = close.pct_change()
    strat_ret = position.shift(1).fillna(0) * daily_ret
    strat_ret = strat_ret.fillna(0.0)
    return strat_ret
