"""Strategy: Wilder Accumulative Swing Index (ASI) price-trend confirmation.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-24-032):
Per J. Welles Wilder's original construction (Investopedia
https://www.investopedia.com/terms/a/asi.asp; formula detail and trading-use
rules from alphasquawk.com's ASI guide
https://alphasquawk.com/accumulative-swing-index-asi-an-in-depth-guide-for-traders/,
both read via browser_exec this iteration after web_search DDGS backend
returned empty results on the first query attempt): ASI is a cumulative
price-swing indicator built from a bar's Swing Index (SI), which measures
"real" price movement using open/high/low/close relationships between the
current and previous bar. The source's own stated trading use is
**confirmation**, not a standalone entry system: "If price is rising and
ASI is also rising, the indicator is confirming the direction of the move."
This is the FIRST Accumulative Swing Index / Wilder Swing Index strategy in
this repo (0 prior KB hits for "Swing Index"/"ASI"/"Accumulative Swing").

Concrete mechanical rule adapted from the source's dual-trendline-agreement
idea (kept simple/testable rather than manual trendline drawing): go long
when BOTH (a) price is above its own SMA(trend_window) [price uptrend] AND
(b) the ASI line is above its own SMA(asi_trend_window) [ASI uptrend] --
i.e. price and the Wilder swing-based indicator agree the trend is up.
Exit when either condition breaks (price drops below its SMA, or ASI drops
below its own SMA), or a max_hold_days time-stop.

Limit-move value (T in Wilder's formula): the source explicitly flags that
stocks/ETFs/crypto have no official exchange limit-move value the way
futures do, and instructs "if you use a proxy, document it" -- this
implementation documents its choice explicitly: T is a fixed proxy equal to
`limit_move_pct` (default 0.03, i.e. 3%) times the previous close, a common
charting-package convention for non-futures markets.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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


def _accumulative_swing_index(df: pd.DataFrame, limit_move_pct: float) -> pd.Series:
    """Wilder's Swing Index (SI) accumulated into the ASI line.

    Formula (Wilder 1978, "New Concepts in Technical Trading Systems"):
        SI = 50 * [((C2-C1) + 0.5*(C2-O2) + 0.25*(C1-O1)) / R] * (K / T)
    where:
        K = max(|H2-C1|, |L2-C1|)
        T = limit_move_pct * C1  (documented non-futures proxy for the
            exchange limit-move value)
        R depends on which of |H2-C1|, |L2-C1|, |H2-L2| is largest:
            if |H2-C1| largest: R = |H2-C1| - 0.5*|L2-C1| + 0.25*|C1-O1|
            if |L2-C1| largest: R = |L2-C1| - 0.5*|H2-C1| + 0.25*|C1-O1|
            if |H2-L2| largest: R = |H2-L2| + 0.25*|C1-O1|
    ASI = cumulative sum of SI.
    """
    o = df["open"] if "open" in df.columns else df["close"].shift(1)
    h = df["high"]
    l = df["low"]
    c = df["close"]

    c1 = c.shift(1)
    o1 = o.shift(1)
    o2 = o
    c2 = c
    h2 = h
    l2 = l

    hc1 = (h2 - c1).abs()
    lc1 = (l2 - c1).abs()
    hl2 = (h2 - l2).abs()
    co1 = (c1 - o1).abs()

    k = pd.concat([hc1, lc1], axis=1).max(axis=1)

    r = pd.Series(np.nan, index=df.index)
    largest = pd.concat([hc1, lc1, hl2], axis=1).idxmax(axis=1)
    # idxmax returns the column label with the largest value among [0,1,2]
    stacked = pd.concat([hc1, lc1, hl2], axis=1)
    stacked.columns = ["hc1", "lc1", "hl2"]
    which = stacked.idxmax(axis=1)

    r_hc1 = hc1 - 0.5 * lc1 + 0.25 * co1
    r_lc1 = lc1 - 0.5 * hc1 + 0.25 * co1
    r_hl2 = hl2 + 0.25 * co1
    r = pd.Series(np.select(
        [which == "hc1", which == "lc1", which == "hl2"],
        [r_hc1, r_lc1, r_hl2],
        default=np.nan,
    ), index=df.index)
    r = r.replace(0.0, np.nan)

    t = limit_move_pct * c1
    t = t.replace(0.0, np.nan)

    numerator = (c2 - c1) + 0.5 * (c2 - o2) + 0.25 * (c1 - o1)
    si = 50.0 * (numerator / r) * (k / t)
    si = si.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    asi = si.cumsum()
    return asi


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    asi_trend_window: int = 20,
    limit_move_pct: float = 0.03,
    max_hold_days: int = 40,
    leverage_cap: float = 1.0,
) -> pd.Series:
    """Return a {0, leverage_cap} long/flat position series.

    Long when price is above its own SMA(trend_window) AND the ASI line is
    above its own SMA(asi_trend_window) -- price/ASI dual-trend agreement
    per the source's stated confirmation-tool use. Exit on either breaking
    down, or a max_hold_days time-stop.
    """
    df = _prep(price_df)
    close = df["close"]

    asi = _accumulative_swing_index(df, limit_move_pct)

    price_sma = close.rolling(trend_window, min_periods=trend_window).mean()
    asi_sma = asi.rolling(asi_trend_window, min_periods=asi_trend_window).mean()

    price_up = close > price_sma
    asi_up = asi > asi_sma
    agree = (price_up & asi_up).fillna(False)

    position = pd.Series(0.0, index=close.index, dtype=float)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if (not bool(agree.iloc[i])) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0.0
                continue
            position.iloc[i] = leverage_cap
        else:
            if bool(agree.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = leverage_cap
            else:
                position.iloc[i] = 0.0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
