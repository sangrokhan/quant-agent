"""Strategy: Laguerre RSI (Ehlers) oversold-recovery-to-overbought-exhaustion
long-only ride.

Hypothesis (knowledge_base/strategies_log.jsonl id TBD, this cron trigger):
Per https://www.quantifiedstrategies.com/laguerre-rsi/ (read via browser_exec
fallback this iteration -- web_search's DDGS backend returned only generic
day-of-week/divergence results for this iteration's queries, and
web_extract's configured backend cannot fetch page content at all, so
browser_exec was used directly for both search and extraction): the Laguerre
RSI is John Ehlers' 4-stage Laguerre-filtered RSI variant -- a smooth
oscillator bounded in [0, 1] with much less whipsaw than classic RSI. The
source's disclosed mean-reversion/trend-capture rule: go long when LRSI
crosses above 0.2 (oversold recovery) and stay long -- NOT exiting
immediately when it reaches overbought -- until LRSI crosses back below 0.8
(momentum exhaustion after an overbought excursion). This captures the full
oversold-bounce-to-overbought-fade move in one continuous hold rather than
scalping the extremes. First Laguerre RSI strategy in this repo (0 prior
matches for "Laguerre" in strategies_index.jsonl).

Laguerre filter (gamma in (0,1), price = close):
    L0 = (1-gamma)*price + gamma*L0[t-1]
    L1 = -gamma*L0 + L0[t-1] + gamma*L1[t-1]
    L2 = -gamma*L1 + L1[t-1] + gamma*L2[t-1]
    L3 = -gamma*L2 + L2[t-1] + gamma*L3[t-1]
CU = sum of positive (L0-L1, L1-L2, L2-L3); CD = sum of abs(negative parts).
LRSI = CU / (CU + CD), in [0, 1].

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series (0/1 position series)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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


def _laguerre_rsi(price: pd.Series, gamma: float = 0.5) -> pd.Series:
    """Ehlers Laguerre RSI: smooth 0..1 oscillator via a 4-stage Laguerre filter."""
    p = price.to_numpy(dtype=float)
    n = len(p)
    l0 = np.zeros(n)
    l1 = np.zeros(n)
    l2 = np.zeros(n)
    l3 = np.zeros(n)
    lrsi = np.full(n, 0.5)

    for i in range(n):
        if i == 0:
            l0[i] = p[i]
            l1[i] = p[i]
            l2[i] = p[i]
            l3[i] = p[i]
            continue
        l0[i] = (1 - gamma) * p[i] + gamma * l0[i - 1]
        l1[i] = -gamma * l0[i] + l0[i - 1] + gamma * l1[i - 1]
        l2[i] = -gamma * l1[i] + l1[i - 1] + gamma * l2[i - 1]
        l3[i] = -gamma * l2[i] + l2[i - 1] + gamma * l3[i - 1]

        cu = 0.0
        cd = 0.0
        d01 = l0[i] - l1[i]
        d12 = l1[i] - l2[i]
        d23 = l2[i] - l3[i]
        for d in (d01, d12, d23):
            if d >= 0:
                cu += d
            else:
                cd += -d
        denom = cu + cd
        lrsi[i] = cu / denom if denom > 1e-12 else 0.5

    return pd.Series(lrsi, index=price.index)


def generate_signals(
    price_df: pd.DataFrame,
    gamma: float = 0.5,
    oversold_threshold: float = 0.2,
    overbought_threshold: float = 0.8,
) -> pd.Series:
    """0/1 long-only position series.

    Entry: LRSI crosses above `oversold_threshold` (from below).
    Exit: LRSI crosses below `overbought_threshold` while already long
    (i.e. it must have gone above `overbought_threshold` at some point
    during the hold, then fades back below it) -- matches the source's
    "ride oversold-bounce through to overbought-exhaustion" rule via a
    simple state machine (enter on the up-cross of oversold, exit on the
    down-cross of overbought).
    """
    df = _prep(price_df)
    close = df["close"]

    lrsi = _laguerre_rsi(close, gamma=gamma)
    lrsi_prev = lrsi.shift(1)

    entry_trigger = (lrsi > oversold_threshold) & (lrsi_prev <= oversold_threshold)
    exit_trigger = (lrsi < overbought_threshold) & (lrsi_prev >= overbought_threshold)

    entry_trigger = entry_trigger.fillna(False).to_numpy()
    exit_trigger = exit_trigger.fillna(False).to_numpy()

    n = len(close)
    position = np.zeros(n)
    in_pos = False
    for i in range(n):
        if in_pos:
            if exit_trigger[i]:
                in_pos = False
            else:
                position[i] = 1.0
        else:
            if entry_trigger[i]:
                in_pos = True
                position[i] = 1.0

    return pd.Series(position, index=close.index)


def generate_returns(
    price_df: pd.DataFrame,
    gamma: float = 0.5,
    oversold_threshold: float = 0.2,
    overbought_threshold: float = 0.8,
) -> pd.Series:
    """Daily strategy returns: prior-day position * that day's simple return."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(
        price_df,
        gamma=gamma,
        oversold_threshold=oversold_threshold,
        overbought_threshold=overbought_threshold,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0.0) * daily_ret
    return strat_ret
