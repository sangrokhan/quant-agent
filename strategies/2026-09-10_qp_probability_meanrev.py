"""Strategy: QP (Quantitativo's Probability) indicator mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl for this run's id):
Per https://www.quantitativo.com/p/a-mean-reversion-strategy-from-first
(visited this iteration), the QP indicator reframes "deviation from the
mean" in terms of empirical probability rather than a bounded oscillator
like RSI(2): for a rolling N-day return window (source default N=3), look
back Y years (source default 5) at the distribution of all historical
N-day returns, then express TODAY's N-day return as a percentile within
that conditional (same-sign) historical distribution, scaled 0-100. A
value near 0 means today's move is an extremely rare drop (or surge);
near 100 means an unremarkable, common-sized move.

    ret_N = pct_change(close, N)
    hist = rolling Y-year window of daily ret_N values, same-sign as today
    if ret_N < 0: QP = 100 * percentile_rank(ret_N within hist[hist<0])
    if ret_N > 0: QP = 100 * (1 - percentile_rank(ret_N within hist[hist>0]))

Source's own cross-sectional S&P 500 strategy (buy QP<15 stocks above their
200d SMA, exit on close>yesterday's high, 4-10 position slots) is not
directly reproducible here -- this repo's data/loaders.py exposes only
single-symbol OHLCV, not a rotating universe. This is a time-series
adaptation applying the identical QP entry/exit mechanics to a SINGLE
traded asset (QQQ/SPY/BTC/ETH) instead of a cross-sectional stock-picking
universe -- first QP-indicator strategy in this repo, distinct from every
RSI/Connors-RSI/PercentRank-of-ROC construction already tested (those rank
a raw indicator value across time, not the conditional-on-sign empirical
percentile of the multi-day return itself).

Signal logic
------------
- Entry (long): close > SMA(trend_window) (uptrend filter, source's own
  200d SMA rule) AND QP < entry_threshold (source default 15 -- a rare
  short-term price drop).
- Exit: close crosses above yesterday's high (source's own disclosed exit
  rule -- "reversion completed"), or a max_hold_days time-stop backstop
  (source's own live version has no hard time-stop; added here as a safety
  net since this is a single-asset adaptation, not a diversified basket).
- Flat otherwise.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
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


def _qp_indicator(close: pd.Series, ret_window: int, lookback_days: int) -> pd.Series:
    """Compute the QP indicator for every bar (vectorized-ish, loop over bars
    since each bar's percentile depends on its own trailing lookback window
    -- unavoidable O(n) rolling-distribution computation, kept simple/clear
    over performance since grid sizes here are modest).
    """
    ret_n = close.pct_change(ret_window)
    qp = pd.Series(np.nan, index=close.index)

    values = ret_n.to_numpy()
    n = len(values)

    for i in range(n):
        today = values[i]
        if np.isnan(today):
            continue
        start = max(0, i - lookback_days)
        window = values[start:i]
        window = window[~np.isnan(window)]
        if len(window) < 30:
            continue

        if today < 0:
            neg = window[window < 0]
            if len(neg) < 10:
                continue
            pct_rank = (neg < today).sum() / len(neg)
            qp.iloc[i] = 100.0 * pct_rank
        elif today > 0:
            pos = window[window > 0]
            if len(pos) < 10:
                continue
            pct_rank = (pos < today).sum() / len(pos)
            qp.iloc[i] = 100.0 * (1.0 - pct_rank)
        else:
            qp.iloc[i] = 50.0

    return qp


def generate_signals(
    price_df: pd.DataFrame,
    ret_window: int = 3,
    lookback_days: int = 1260,  # ~5 trading years
    entry_threshold: float = 15.0,
    trend_window: int = 200,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    qp = _qp_indicator(close, ret_window, lookback_days)
    ret_n = close.pct_change(ret_window)
    sma = close.rolling(trend_window).mean()
    prior_high = close.shift(1)  # yesterday's close used as the "yesterday's high" proxy
    # NOTE: our loaders provide OHLCV, so use the actual high column when present.
    if "high" in df.columns:
        prior_high = df["high"].shift(1)

    entry_signal = (ret_n < 0) & (qp.notna()) & (qp < entry_threshold) & (close > sma)
    exit_signal = close > prior_high

    valid = qp.notna() & sma.notna()

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = None

    for i in range(len(df.index)):
        if not valid.iloc[i]:
            position.iloc[i] = 0
            continue

        if in_position:
            held_days = i - entry_idx
            if exit_signal.iloc[i] or held_days >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if entry_signal.iloc[i]:
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    ret_window: int = 3,
    lookback_days: int = 1260,
    entry_threshold: float = 15.0,
    trend_window: int = 200,
    max_hold_days: int = 15,
) -> pd.Series:
    """Daily strategy returns (position-weighted, no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        ret_window=ret_window,
        lookback_days=lookback_days,
        entry_threshold=entry_threshold,
        trend_window=trend_window,
        max_hold_days=max_hold_days,
    )

    daily_ret = close.pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0).astype(int) * daily_ret
    strat_returns.name = "strategy_returns"
    return strat_returns
