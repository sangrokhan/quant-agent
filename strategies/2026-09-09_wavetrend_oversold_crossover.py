"""Strategy: WaveTrend Oscillator (LazyBear) WT1/WT2 crossover from
oversold territory.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-055):
Per pineify.app's WaveTrend Oscillator Pine Script guide (exact formula)
and Bing's AI-overview aggregation of the indicator's own entry/exit rules
(browser_exec fallback -- web_search's DuckDuckGo backend errored with
"No results found" for the raw query), the WaveTrend Oscillator normalizes
price deviation by its own volatility (mean absolute deviation), giving a
self-adjusting oscillator distinct from RSI/CCI. Formula: ap=HLC3 (typical
price), esa=EMA(ap,N), d=EMA(|ap-esa|,N), ci=(ap-esa)/(0.015*d),
WT1=EMA(ci,M), WT2=SMA(WT1,4) (default N=10, M=21). Source's own explicit
"Golden Cross" buy rule: WT1 crosses above WT2 while the oscillator sits
below the oversold zone (~-60) -- explicitly filtering out neutral-zone
(-40 to +40) crossovers as "choppy, directionless" false signals. Exit:
WT1 crosses below WT2 (source's "Death Cross" reversal signal).

First WaveTrend Oscillator strategy in this repo (0 prior hits on
"Wave Trend"/"WaveTrend" in strategies_index.jsonl).

Signal logic
------------
- ap = (high + low + close) / 3
- esa = EMA(ap, channel_len)
- d = EMA(|ap - esa|, channel_len)
- ci = (ap - esa) / (0.015 * d)
- WT1 = EMA(ci, avg_len)
- WT2 = SMA(WT1, 4)
- Entry (long): WT1 crosses above WT2 AND WT1 (at the cross) is below
  `oversold_level` (source's own explicit "avoid neutral-zone crossovers"
  filter).
- Exit: WT1 crosses below WT2, OR a max_hold_days time-stop.

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


def _wavetrend(df: pd.DataFrame, channel_len: int, avg_len: int) -> tuple[pd.Series, pd.Series]:
    ap = (df["high"] + df["low"] + df["close"]) / 3.0
    esa = ap.ewm(span=channel_len, adjust=False).mean()
    d = (ap - esa).abs().ewm(span=channel_len, adjust=False).mean()
    ci = (ap - esa) / (0.015 * d.replace(0, float("nan")))
    wt1 = ci.ewm(span=avg_len, adjust=False).mean()
    wt2 = wt1.rolling(4).mean()
    return wt1, wt2


def generate_signals(
    price_df: pd.DataFrame,
    channel_len: int = 10,
    avg_len: int = 21,
    oversold_level: float = -60.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    wt1, wt2 = _wavetrend(df, channel_len, avg_len)

    cross_up = (wt1 > wt2) & (wt1.shift(1) <= wt2.shift(1))
    cross_down = (wt1 < wt2) & (wt1.shift(1) >= wt2.shift(1))
    from_oversold = wt1 < oversold_level

    entry_signal = cross_up & from_oversold

    position = pd.Series(0, index=close.index, dtype=int)
    in_pos = False
    entry_idx = -1
    for i in range(len(close)):
        if not in_pos:
            es = entry_signal.iloc[i]
            if bool(es) if pd.notna(es) else False:
                in_pos = True
                entry_idx = i
                position.iloc[i] = 1
        else:
            held = i - entry_idx
            cd = cross_down.iloc[i]
            cd_bool = bool(cd) if pd.notna(cd) else False
            if cd_bool or held >= max_hold_days:
                in_pos = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
    return position


def generate_returns(
    price_df: pd.DataFrame,
    channel_len: int = 10,
    avg_len: int = 21,
    oversold_level: float = -60.0,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return daily strategy returns (position-weighted, no txn costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        channel_len=channel_len,
        avg_len=avg_len,
        oversold_level=oversold_level,
        max_hold_days=max_hold_days,
    )
    daily_ret = close.pct_change()
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret.fillna(0.0)
