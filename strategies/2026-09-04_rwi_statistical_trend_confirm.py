"""Strategy: Random Walk Index (RWI) statistical trend confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-153):
The Random Walk Index (Michael Poulos) compares actual price movement over
n periods to what a pure random walk would produce, normalized by ATR:
RWI High = (High - Low[n bars ago]) / (ATR(n) * sqrt(n)), RWI Low =
(High[n bars ago] - Low) / (ATR(n) * sqrt(n)). Per LightningChart's
explainer, RWI High > threshold (commonly 1.0) while RWI Low < threshold
signals a statistically-significant uptrend (price moved further than
random chance would predict); RWI Low dominating signals a downtrend; both
below threshold means the move is statistically indistinguishable from
noise. This strategy: long entry when RWI High crosses above the threshold
while RWI Low is below it (confirmed statistical uptrend, not noise); exit
when RWI High drops back below the threshold or RWI Low rises above RWI
High (trend confirmation breaks down), or a max_hold_days time-stop. First
Random Walk Index strategy in this repo -- distinct from VHF/ADX/Choppiness
Index (already tested, all trend-strength-not-direction concepts) since
RWI directly compares to a statistical random-walk null hypothesis rather
than a raw range-vs-path ratio.

Signal logic
------------
- ATR = Average True Range(n)
- RWI_high[t] = (high[t] - low[t-n]) / (ATR[t] * sqrt(n))
- RWI_low[t] = (high[t-n] - low[t]) / (ATR[t] * sqrt(n))
- Entry (long): RWI_high crosses above rwi_threshold AND RWI_low <
  rwi_threshold (confirmed statistical uptrend).
- Exit: RWI_high < rwi_threshold, OR RWI_low > RWI_high (trend
  confirmation lost), OR max_hold_days elapsed.
- Flat otherwise.
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


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def _rwi(df: pd.DataFrame, n: int) -> tuple[pd.Series, pd.Series]:
    atr = _atr(df, n)
    denom = atr * (n ** 0.5)
    denom = denom.replace(0.0, np.nan)
    rwi_high = (df["high"] - df["low"].shift(n)) / denom
    rwi_low = (df["high"].shift(n) - df["low"]) / denom
    return rwi_high.fillna(0.0), rwi_low.fillna(0.0)


def generate_signals(
    price_df: pd.DataFrame,
    n: int = 14,
    rwi_threshold: float = 1.0,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    rwi_high, rwi_low = _rwi(df, n)

    cross_up = (rwi_high > rwi_threshold) & (rwi_high.shift(1) <= rwi_threshold)
    entry_raw = (cross_up & (rwi_low < rwi_threshold)).fillna(False).to_numpy()

    exit_raw = ((rwi_high < rwi_threshold) | (rwi_low > rwi_high)).fillna(True).to_numpy()

    pos_arr = [0] * len(df)
    in_pos = False
    hold_days = 0
    for i in range(len(df)):
        if in_pos:
            hold_days += 1
            if exit_raw[i] or hold_days >= max_hold_days:
                in_pos = False
                hold_days = 0
                pos_arr[i] = 0
            else:
                pos_arr[i] = 1
        else:
            if entry_raw[i]:
                in_pos = True
                hold_days = 0
                pos_arr[i] = 1
            else:
                pos_arr[i] = 0

    return pd.Series(pos_arr, index=df.index, dtype=int)


def generate_returns(
    price_df: pd.DataFrame,
    n: int = 14,
    rwi_threshold: float = 1.0,
    max_hold_days: int = 20,
) -> pd.Series:
    df = _prep(price_df)
    position = generate_signals(
        price_df,
        n=n,
        rwi_threshold=rwi_threshold,
        max_hold_days=max_hold_days,
    )
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
