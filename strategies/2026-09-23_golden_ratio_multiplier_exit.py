"""Strategy: Golden Ratio Multiplier Cycle-Top Sell Signal (Philip Swift).

Hypothesis (2026-09-23, 9th iteration this cron trigger):
Per the Golden Ratio Multiplier (Philip Swift / @PositiveCrypto, Medium
article; corroborated by Bitbo Charts, Coinfuty, and Look Into Bitcoin,
found via browser_exec after web_search DDGS/Yahoo backend TLS-errored
this iteration): the daily 350-day simple moving average (SMA350) of
Bitcoin's price, multiplied by a ladder of Fibonacci-adjacent ratios
(1.6, 2, 3, 5, 8, 13), has historically framed prior market-cycle tops --
the ratio bands act as resistance levels the price approaches/exceeds
near cycle peaks, and the base SMA350 (or its 1.6x multiple, per the
"Golden Ratio" itself) has historically framed cycle-BOTTOM support.

Operationalized as a regime-exit rule (not multi-target scaling, which
would need position-tranching beyond this repo's binary/continuous
position contract): go long whenever close is below `overheat_multiplier`
times the SMA350 (i.e. NOT yet near/above the lower cycle-top warning
band); exit to flat whenever close exceeds `overheat_multiplier` x SMA350
(the lowest disclosed multiplier rung, 1.6x, used as the earliest/most
conservative sell trigger) until price falls back below `reentry_multiplier`
x SMA350 (hysteresis to avoid immediate re-entry chop right at the band).

Distinct from every prior strategy in this repo: this is the first
strategy using a MOVING-AVERAGE-MULTIPLE band (not a raw price level, ATR
band, or Bollinger-style std-dev band) as a cycle-top resistance/exit
signal, and the first using the specific 350-day SMA lookback with
Fibonacci-ratio multipliers (distinct from the already-rejected 200-week
[1400-day] MA momentum strategy this same cron trigger, which used the
200WMA's own rate of CHANGE, not price-vs-multiple-of-MA).

Tested on BTC/ETH (the source's own target asset) and QQQ/SPY as a
falsification check (no comparable "cycle multiplier" folklore exists for
equity indices, though the mechanical band construction is computable on
any asset).
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    sma_window: int = 350,
    overheat_multiplier: float = 1.6,
    reentry_multiplier: float = 1.3,
) -> pd.Series:
    """Return a {0,1} long/flat position series with hysteresis:
    exit when close > overheat_multiplier * SMA(sma_window);
    re-enter when close < reentry_multiplier * SMA(sma_window);
    hold prior state in between."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(sma_window, min_periods=max(30, sma_window // 4)).mean()
    upper_band = sma * overheat_multiplier
    lower_band = sma * reentry_multiplier

    n = len(close)
    close_vals = close.to_numpy()
    upper_vals = upper_band.to_numpy()
    lower_vals = lower_band.to_numpy()
    sma_vals = sma.to_numpy()

    state = [False] * n  # True = long
    prev = False
    for i in range(n):
        if pd.isna(sma_vals[i]):
            state[i] = False
            continue
        c = close_vals[i]
        if c > upper_vals[i]:
            prev = False
        elif c < lower_vals[i]:
            prev = True
        state[i] = prev

    position = pd.Series([1 if s else 0 for s in state], index=close.index)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs). Position lagged by 1 day."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
