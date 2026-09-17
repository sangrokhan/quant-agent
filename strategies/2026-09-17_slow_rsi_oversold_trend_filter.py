"""Strategy: Slow RSI (SRSI) Oversold Reversal with SMA Trend Filter
(Vitali Apirine, "The Slow Relative Strength Index", TASC April 2015; code
republished in TASC July 2015 Traders' Tips), read this iteration via
browser_exec at
https://traders.com/Documentation/FEEDbk_docs/2015/07/TradersTips.html
(exact TradeStation EasyLanguage function/indicator code disclosed directly
in the Traders' Tips section, after web_search DDGS backend errored on
prior queries this run -- direct traders.com archive URL navigation to a
previously-unvisited month, discovered by walking forward from adjacent
known TASC months already in this repo's visited_urls.jsonl ledger).

Hypothesis (see knowledge_base/strategies_log.jsonl entry for this id):
Apirine's SRSI applies Wilder's RSI recursive net-change/total-change
smoothing NOT to raw price, but to an EXPONENTIALLY-SMOOTHED price series
first (`Price = XAverage(iPrice, SmoothingLength)`), producing a
double-smoothed oscillator intended to reduce whipsaw relative to standard
RSI while retaining a comparable 0-100 (rescaled via `50*(ChgRatio+1)`)
range. This is distinct from every other RSI-family construction in this
repo (classic RSI, StochRSI, Cutler's RSI, Connors RSI, Dynamic Zone RSI,
Vervoort Rainbow-smoothed RSI) because the smoothing happens to the PRICE
INPUT before RSI's own recursive averaging is applied, rather than to the
RSI output or via a different lookback windowing scheme. First Slow RSI
(Apirine, TASC Apr/Jul 2015) strategy in this repo.

Exact formula (from TASC Jul 2015 TradeStation EasyLanguage, as read this
iteration):
    Price = EMA(Close, smoothing_length)
    NetChgAvg[0] = (Price[0] - Price[-length]) / length   (seed at bar=length)
    TotChgAvg[0] = SMA(|Price - Price[-1]|, length)        (seed at bar=length)
    for subsequent bars (Wilder-style recursive smoothing, SF=1/length):
        NetChgAvg[t] = NetChgAvg[t-1] + SF*(Change[t] - NetChgAvg[t-1])
        TotChgAvg[t] = TotChgAvg[t-1] + SF*(|Change[t]| - TotChgAvg[t-1])
    ChgRatio = NetChgAvg / TotChgAvg  (0 if TotChgAvg==0)
    SRSI = 50 * (ChgRatio + 1)

Trading rule (this iteration's own addition -- the source article/Traders'
Tips only disclosed the SRSI function/indicator, no explicit strategy
rule, so per this repo's established convention for TASC "function only"
entries, a standard oversold-reversal rule is applied, gated by an
SMA(trend_window) uptrend filter, consistent with this repo's other RSI
oversold-reversal entries): long entry when SRSI crosses above `oversold`
from below AND close > SMA(trend_window); exit on SRSI crossing above
`overbought`, the trend filter breaking, or a `max_hold_days` time-stop.

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


def _srsi(close: pd.Series, length: int, smoothing_length: int) -> pd.Series:
    price = close.ewm(span=smoothing_length, adjust=False).mean()
    n = len(price)
    price_vals = price.values

    net_chg_avg = np.full(n, np.nan)
    tot_chg_avg = np.full(n, np.nan)
    sf = 1.0 / length

    if n <= length:
        return pd.Series(np.full(n, 50.0), index=close.index)

    # seed at index `length` (0-indexed: CurrentBar==length+1 in EasyLanguage's
    # 1-indexed CurrentBar==1 convention roughly maps to python idx==length)
    seed_idx = length
    net_chg_avg[seed_idx] = (price_vals[seed_idx] - price_vals[seed_idx - length]) / length
    changes_window = np.abs(np.diff(price_vals[seed_idx - length : seed_idx + 1]))
    tot_chg_avg[seed_idx] = changes_window.mean() if len(changes_window) else 0.0

    for i in range(seed_idx + 1, n):
        change = price_vals[i] - price_vals[i - 1]
        net_chg_avg[i] = net_chg_avg[i - 1] + sf * (change - net_chg_avg[i - 1])
        tot_chg_avg[i] = tot_chg_avg[i - 1] + sf * (abs(change) - tot_chg_avg[i - 1])

    chg_ratio = np.where(tot_chg_avg != 0, net_chg_avg / tot_chg_avg, 0.0)
    srsi = 50.0 * (chg_ratio + 1.0)
    srsi[:seed_idx] = 50.0
    return pd.Series(srsi, index=close.index)


def generate_signals(
    price_df: pd.DataFrame,
    rsi_length: int = 14,
    smoothing_length: int = 5,
    oversold: float = 30.0,
    overbought: float = 70.0,
    trend_window: int = 100,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series per the SRSI oversold-reversal rule."""
    df = _prep(price_df)
    close = df["close"]
    n = len(df)

    srsi = _srsi(close, rsi_length, smoothing_length)
    sma_trend = close.rolling(trend_window).mean()
    uptrend = close > sma_trend

    cross_up_from_oversold = (srsi > oversold) & (srsi.shift(1) <= oversold)
    cross_over_overbought = (srsi > overbought) & (srsi.shift(1) <= overbought)

    cu_vals = cross_up_from_oversold.values
    co_vals = cross_over_overbought.values
    uptrend_vals = uptrend.values
    valid_vals = srsi.notna().values & sma_trend.notna().values

    position = np.zeros(n, dtype=int)
    in_long = False
    entry_bar = -1
    for i in range(n):
        if not valid_vals[i]:
            position[i] = 0
            continue
        if not in_long:
            if cu_vals[i] and uptrend_vals[i]:
                in_long = True
                entry_bar = i
        else:
            held = i - entry_bar
            if co_vals[i] or (not uptrend_vals[i]) or held >= max_hold_days:
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
