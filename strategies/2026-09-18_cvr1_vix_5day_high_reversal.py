"""Strategy: CVR1 VIX Market Timing (Larry Connors, "Connors VIX Reversals").

Hypothesis (see knowledge_base/strategies_log.jsonl for this iteration's id):
Per CMT Association's "Technically Speaking, April 2012" transcript (Landry
Trading interview, https://cmtassociation.org/technically_speaking/technically-speaking-april-2012/,
read via browser_exec after web_search DDGS backend surfaced only indirect
snippets -- this repo's prior attempt at this indicator, 2026-09-11-126,
explicitly noted CVR1's exact numeric rule "not findable free" at the time;
this iteration found the exact disclosed rule), CVR1 is the most basic of
Connors' 10 VIX Reversal signals:

"The rules for the CVR 1 are simple: For market buys, we are looking for
the VIX to make a 5-day high and close under its open."

Rationale (source's own): a 5-day VIX high signals the market has reached a
short-term fear extreme; VIX closing below its own open on that same day
(despite hitting a new high) signals fear is *already starting to fade*
intraday -- an earlier/more sensitive reversal-timing signal than CVR3
(already tested in this repo, 2026-09-05-021/2026-09-08-080/2026-09-11-018,
which requires VIX to be 10% above its 10-day SMA -- a slower, more extreme
threshold). Source explicitly states CVR1 predicts correctly only ~59% of
the time (its weakest single signal) but is included here for its
economically-distinct entry logic (5-day-high + down-close-vs-open, no
moving-average-distance requirement at all) rather than expecting a
standalone edge as strong as CVR3.

Exit: source's own stated rule for CVR3 (extended here to CVR1, following
this repo's existing CVR3 implementation's convention since CVR1's own
exit rule isn't separately disclosed in the source): exit when VIX trades
intraday below yesterday's 10-day SMA (mean reversion), or a fixed 2-4 day
hold, whichever comes first.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position series)

Note: `price_df` is the TRADABLE asset (SPY/QQQ/BTC-USDT/ETH-USDT); VIX data
is fetched internally via data/loaders.load_equity("^VIX", ...) aligned to
price_df's date range, matching this repo's existing CVR3 implementation
pattern (strategies/2026-09-05_cvr3_vix_market_timing.py).
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
    high_lookback_days: int = 5,
    min_hold_days: int = 2,
    max_hold_days: int = 4,
) -> pd.Series:
    """Return a {0,1} long/flat position series on the TRADABLE asset in
    price_df, driven by VIX-based CVR1 buy/exit signals."""
    df = _prep(price_df)
    close = df["close"]

    vix = _fetch_vix(df.index)
    vix_sma10 = vix["close"].rolling(10).mean()

    # CVR1 buy signal: VIX makes a high_lookback_days-day HIGH (close at a
    # fresh N-day extreme) AND closes BELOW its own open that day.
    vix_rolling_high = vix["close"].rolling(high_lookback_days).max()
    cond_5day_high = vix["close"] >= vix_rolling_high
    cond_close_below_open = vix["close"] < vix["open"]
    vix_buy_signal = (cond_5day_high & cond_close_below_open).fillna(False)

    entry = vix_buy_signal.reindex(close.index, method="ffill").fillna(False)

    # Exit rule (per source's CVR3 exit convention, extended to CVR1):
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
