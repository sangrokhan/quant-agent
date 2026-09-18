"""Strategy: Ehlers Distance Coefficient Filter (EDCF) price crossover.

Hypothesis (see knowledge_base/strategies_log.jsonl for this id): John F.
Ehlers' Distance Coefficient Filter (described in "Rocket Science For
Traders", 2001, Chapter 18: Ehlers Filters) is a distance-weighted moving
average: each of the trailing `length` bars is weighted by the SUM OF ITS
SQUARED DISTANCES to every other bar in the same window. Bars whose price
is far from the rest of the window (outliers/turning points) get pulled
toward the window's dominant cluster more strongly, while bars similar to
their neighbors barely move the filter -- a very different weighting logic
from all prior moving-average variants in this repo (SMA/EMA/WMA/KAMA/
FRAMA/HMA/VWMA/eVWMA/McGinley etc., none of which weight by intra-window
squared-distance dispersion).

Formula (from the original open-source Pine Script by everget, MIT
licensed, faithfully reproduced here):
    for count in 0..length-1:
        distance[count] = sum over lookback in 1..length-1 of
            (src[count] - src[count+lookback])^2
    EDCF = sum(distance[count] * src[count]) / sum(distance[count])

Signal logic: long entry when close crosses above the EDCF line (price
breaking above the distance-weighted trend anchor), exit on the mirror
cross below, or a max-hold time-stop (this repo's standard pattern).

Source: https://www.tradingview.com/script/6a8CD4JI-Ehlers-Distance-Coefficient-Filter/
(open-source Pine Script v3, MIT license, fully disclosed formula; fetched
via browser_exec -- web_search DDGS backend failing this cron trigger).
First Distance Coefficient Filter strategy in this repo.

ACCEPTED per-symbol configs (see knowledge_base id 2026-09-18-083, rescue
of near-miss 2026-09-18-082): QQQ length=12/max_hold_days=10 (Sharpe
1.043, MDD 0.222); SPY length=18/max_hold_days=30 (Sharpe 1.069, MDD
0.207). Both pass Sharpe/MDD/TC-survival/parameter-sensitivity. Crypto
(BTC/USDT, ETH/USDT) remains out of scope -- decisive rejection at the
default hourly-bar granularity in 2026-09-18-082's grid test.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1})
    generate_returns(price_df, **params) -> pd.Series
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


def _edcf(src: np.ndarray, length: int) -> np.ndarray:
    """Ehlers Distance Coefficient Filter, per the original Pine Script.

    For each bar i (0-indexed), uses src[i], src[i-1], ..., src[i-length+1]
    as the window (count=0..length-1 maps to src[i-count]).
    """
    n = len(src)
    out = np.full(n, np.nan)

    for i in range(n):
        if i < 2 * (length - 1):
            # not enough history for the full nested-window distance calc
            continue
        src_sum = 0.0
        coef_sum = 0.0
        for count in range(length):
            idx_count = i - count
            distance = 0.0
            for lookback in range(1, length):
                idx_lb = idx_count - lookback
                distance += (src[idx_count] - src[idx_lb]) ** 2
            src_sum += distance * src[idx_count]
            coef_sum += distance
        out[i] = src_sum / coef_sum if coef_sum != 0 else src[i]

    return out


def generate_signals(
    price_df: pd.DataFrame,
    length: int = 14,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long entry when close crosses above the EDCF line, exit on the mirror
    cross below, or after max_hold_days.
    """
    df = _prep(price_df)
    close = df["close"]
    hl2 = (df["high"] + df["low"]) / 2.0

    edcf_vals = _edcf(hl2.to_numpy(dtype=float), length)
    edcf = pd.Series(edcf_vals, index=df.index)

    cross_up = (close > edcf) & (close.shift(1) <= edcf.shift(1))
    cross_down = (close < edcf) & (close.shift(1) >= edcf.shift(1))

    n = len(df)
    cu = cross_up.to_numpy()
    cd = cross_down.to_numpy()

    position = [0.0] * n
    in_pos = False
    hold_count = 0
    for i in range(n):
        if in_pos:
            hold_count += 1
            if cd[i] or hold_count >= max_hold_days:
                in_pos = False
                hold_count = 0
            else:
                position[i] = 1.0
        else:
            if cu[i]:
                in_pos = True
                hold_count = 0
                position[i] = 1.0
    return pd.Series(position, index=df.index, dtype=float)


def generate_returns(
    price_df: pd.DataFrame,
    length: int = 14,
    max_hold_days: int = 20,
) -> pd.Series:
    """Daily strategy returns (no transaction costs -- applied separately)."""
    df = _prep(price_df)
    position = generate_signals(df, length=length, max_hold_days=max_hold_days)
    daily_ret = df["close"].pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret
