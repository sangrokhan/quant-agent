"""Strategy: CVR9 VIX Market Timing (Larry Connors, "Connors VIX Reversals").

Hypothesis (see knowledge_base/strategies_log.jsonl id 2026-09-20-028):
Per Docsity's "CMT Level 3 Exam Q&A: Technical Analysis and Trading
Systems" study material (surfaced via Google SERP snippet, read via
browser_exec after web_search's DDGS backend errored with a TLS
RequestError on this iteration's query "CVR9 VIX Reversal exact rule"):

"Connors VIX Reversal 9 (CVR9) Strategy. Buy/Sell Rules. Today's VIX high
must be higher than high of last 10 days. Today's VIX must close below its
open."

This repo already has CVR1 (2026-09-18-141: VIX 5-day high + close-below-
open, accepted) and CVR3 (2026-09-05-021/2026-09-08-080/2026-09-11-018: VIX
10% above its 10-day SMA, accepted QQQ). CVR9 is a DISTINCT, separately
documented Connors signal from both: unlike CVR1's shorter 5-day lookback,
CVR9 requires today's VIX high to exceed the prior 10 trading days' highs
(a more extreme, less frequent fear-spike signal, closer to CVR3's severity
but using an absolute rolling-high condition rather than CVR3's
distance-from-SMA condition) -- economically this should fire on rarer,
sharper VIX spikes than CVR1, giving fewer but (per Connors' own commentary
on the CVR family, higher-severity signals tending to be historically more
reliable than CVR1's ~59% single-signal hit rate) potentially
higher-conviction trades. Exit: source's own CVR3 exit convention
(extended here, following this repo's CVR1/CVR3 implementation pattern,
since CVR9's own exit isn't separately disclosed in the Docsity source):
exit when VIX trades intraday below yesterday's 10-day SMA (mean
reversion), or a fixed min/max-day hold, whichever comes first.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position series)

Note: `price_df` is the TRADABLE asset (SPY/QQQ/BTC-USDT/ETH-USDT); VIX data
is fetched internally via data/loaders.load_equity("^VIX", ...) aligned to
price_df's date range, matching this repo's existing CVR1/CVR3
implementation pattern.
"""

from __future__ import annotations

import sys
import os
from datetime import datetime, timezone

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity  # noqa: E402


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _fetch_vix(index: pd.DatetimeIndex) -> pd.DataFrame:
    start = index.min().to_pydatetime()
    end = index.max().to_pydatetime()
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    vix = load_equity("^VIX", start, end)
    return _prep(vix)


def generate_signals(
    price_df: pd.DataFrame,
    high_lookback_days: int = 10,
    min_hold_days: int = 2,
    max_hold_days: int = 4,
) -> pd.Series:
    """Return a {0,1} long/flat position series on the TRADABLE asset in
    price_df, driven by VIX-based CVR9 buy/exit signals."""
    df = _prep(price_df)
    close = df["close"]

    vix = _fetch_vix(df.index)
    vix_sma10 = vix["close"].rolling(10).mean()

    # CVR9 buy signal: today's VIX HIGH exceeds the prior high_lookback_days
    # days' highs (a fresh N-day extreme using the intraday high, per the
    # source's own wording "today's VIX high must be higher than high of
    # last 10 days") AND closes BELOW its own open that day.
    prior_high = vix["high"].rolling(high_lookback_days).max().shift(1)
    cond_10day_high = vix["high"] > prior_high
    cond_close_below_open = vix["close"] < vix["open"]
    vix_buy_signal = (cond_10day_high & cond_close_below_open).fillna(False)

    entry = vix_buy_signal.reindex(close.index, method="ffill").fillna(False)

    # Exit rule (per source's CVR3 exit convention, extended to CVR9,
    # matching this repo's existing CVR1 implementation):
    # exit when VIX trades intraday below yesterday's 10-day SMA.
    prior_day_sma = vix_sma10.shift(1)
    vix_exit_signal = (vix["close"] < prior_day_sma).reindex(close.index, method="ffill").fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            exit_ok = held >= min_hold_days
            if (exit_ok and bool(vix_exit_signal.iloc[i])) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
                in_position = True
                entry_idx = i
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
