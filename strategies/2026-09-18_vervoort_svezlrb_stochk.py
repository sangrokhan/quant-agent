"""Strategy: Sylvain Vervoort's Zero-Lag Rainbow-Smoothed %b Oscillator
(SVEZLRBPercB) + smoothed StochK confirmation.

Hypothesis (knowledge_base id TBD, this cron trigger):
Sylvain Vervoort's "Oscillators, Smoothed" article (TASC September 2013,
https://traders.com/Documentation/FEEDbk_docs/2013/09/TradersTips.html,
read this iteration via browser_exec -- web_search DDGS backend failed with
repeated TLS connection errors on this iteration's queries) discloses two
related indicators:

1. SVEZLRBPercB (a zero-lag "%b" oscillator): close is cascaded through a
   10-stage 2-period SMA pyramid ("Rainbow" smoothing, weighted 5/4/3/2/1
   for the first five stages, 1 each for the rest, /20), then
   double-EMA-smoothed (zero-lag correction: zlrb = ema1 - (ema1 - ema2)),
   then TEMA-smoothed, then normalized against its own rolling
   mean +/- 2*std over stdev_period (a %b-style [0,100] percent-of-band
   position).
2. A companion smoothed Stochastic %K computed off "rbc" (Rainbow smoothed
   value averaged with typical price) over period_k, slowed by smooth_k.

Per this repo's web-search results (Wealth-Lab TASC page, Scribd PDF
excerpt, ThinkOrSwim strategy docs), Vervoort's own demo strategy uses just
two basic rules: "buy when the StochK crosses above from oversold
territory, and sell when it leaves the overbought zone" -- i.e. a
stochastic oversold-recovery / overbought-exit rule, using the %b oscillator
as the underlying smoothed-price context rather than a separate trigger.
This repo has 0 prior entries for SVEZLRBPercB specifically (distinct from
already-tested Vervoort Ergodic/ZLRSI/HACOLT -- this is Vervoort's
zero-lag-Rainbow %b + Stochastic combo, a different construction: no other
prior entry uses the 10-stage Rainbow SMA cascade + zero-lag EMA correction
+ %b-style rolling-band normalization).

Long entry: smoothed StochK crosses above the oversold level (30, per the
source's own convention for a stochastic-style oscillator) from below;
exit: StochK crosses below the overbought level (70) after having been
above it, or a max_hold_days time-stop, or a trend-filter break (this
repo's standard SMA(trend_window) uptrend gate added since the raw
oscillator crossover is not itself trend-aware, following this repo's
established rescue pattern for raw stochastic-style crossovers).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position).
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


def _rainbow_value(close: pd.Series) -> pd.Series:
    """10-stage cascaded 2-period SMA pyramid, weighted 5/4/3/2/1/1/1/1/1/1 / 20."""
    sma = [close]
    for _ in range(10):
        sma.append(sma[-1].rolling(2).mean())
    # sma[1..10] are SMAValue1..SMAValue10
    weights = [5, 4, 3, 2, 1, 1, 1, 1, 1, 1]
    rainbow = sum(w * sma[i + 1] for i, w in enumerate(weights)) / 20.0
    return rainbow


def _svezlrb_percb(df: pd.DataFrame, smooth: int, stdev_period: int) -> pd.Series:
    close = df["close"]
    rainbow = _rainbow_value(close)
    ema1 = rainbow.ewm(span=smooth, adjust=False).mean()
    ema2 = ema1.ewm(span=smooth, adjust=False).mean()
    diff = ema1 - ema2
    zlrb = ema1 - diff  # zero-lag corrected

    def _tema(s: pd.Series, span: int) -> pd.Series:
        e1 = s.ewm(span=span, adjust=False).mean()
        e2 = e1.ewm(span=span, adjust=False).mean()
        e3 = e2.ewm(span=span, adjust=False).mean()
        return 3 * e1 - 3 * e2 + e3

    center = _tema(zlrb, smooth)
    std = center.rolling(stdev_period).std()
    wma_center = center.rolling(stdev_period).apply(
        lambda x: np.average(x, weights=np.arange(1, len(x) + 1)), raw=True
    )
    percb = (center + 2 * std - wma_center) / (4 * std.replace(0.0, np.nan)) * 100.0
    return percb


def _stoch_k(df: pd.DataFrame, period_k: int, smooth_k: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    rainbow = _rainbow_value(close)
    typical = (high + low + close) / 3.0
    rbc = (rainbow + typical) / 2.0

    hh = high.rolling(period_k).max()
    ll = rbc.rolling(period_k).min()
    denom = (hh - ll).replace(0.0, np.nan)
    fast_k = ((rbc - low.rolling(period_k).min()) / denom * 100.0).clip(0, 100)
    slow_k = fast_k.rolling(smooth_k).mean()
    return slow_k


def generate_signals(
    price_df: pd.DataFrame,
    smooth: int = 3,
    stdev_period: int = 18,
    period_k: int = 30,
    smooth_k: int = 3,
    oversold: float = 30.0,
    overbought: float = 70.0,
    trend_window: int = 150,
    max_hold_days: int = 30,
) -> pd.Series:
    """Long-only 0/1 position: StochK oversold-recovery entry, overbought-exit,
    gated by an SMA(trend_window) uptrend filter and a max_hold_days time-stop.
    """
    df = _prep(price_df)
    close = df["close"]

    stoch_k = _stoch_k(df, period_k, smooth_k)
    trend_long = close > close.rolling(trend_window).mean()

    was_oversold = (stoch_k < oversold).shift(1).fillna(False)
    cross_up = was_oversold & (stoch_k >= oversold)

    was_overbought = (stoch_k > overbought).shift(1).fillna(False)
    cross_down = was_overbought & (stoch_k <= overbought)

    n = len(df)
    position = np.zeros(n, dtype=float)
    in_pos = False
    entry_idx = -1
    cross_up_arr = cross_up.to_numpy()
    cross_down_arr = cross_down.to_numpy()
    trend_arr = trend_long.fillna(False).to_numpy()

    for i in range(n):
        if in_pos:
            held = i - entry_idx
            if cross_down_arr[i] or (not trend_arr[i]) or held >= max_hold_days:
                in_pos = False
        else:
            if cross_up_arr[i] and trend_arr[i]:
                in_pos = True
                entry_idx = i
        position[i] = 1.0 if in_pos else 0.0

    return pd.Series(position, index=df.index)


def generate_returns(
    price_df: pd.DataFrame,
    smooth: int = 3,
    stdev_period: int = 18,
    period_k: int = 30,
    smooth_k: int = 3,
    oversold: float = 30.0,
    overbought: float = 70.0,
    trend_window: int = 150,
    max_hold_days: int = 30,
) -> pd.Series:
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        smooth=smooth,
        stdev_period=stdev_period,
        period_k=period_k,
        smooth_k=smooth_k,
        oversold=oversold,
        overbought=overbought,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret
