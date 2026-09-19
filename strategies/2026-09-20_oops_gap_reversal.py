"""Strategy: Larry Williams "Oops!" gap reversal pattern (daily-bar adaptation).

Hypothesis (see knowledge_base/strategies_log.jsonl id 2026-09-20-032):
Larry Williams' classic "Oops!" pattern (per multiple converging sources
read via browser_exec this iteration -- FTMO.com, Oxfordstrat R&D blog
snippet, TradingView xtradernet script snippet, tradingcoachu.com summary
-- web_search DDGS backend was not attempted this iteration given the
established pattern of TLS failures earlier this cron trigger, browser_exec
Google SERP used directly):

"For a buy signal, look for the market to open below the previous day's
low [a gap down beyond yesterday's low]... Place a buy [stop] at the level
of yesterday's low... reverses upward and breaks through yesterday's low,
your order is triggered." The mirror short-side rule (not implemented here,
long-only per this repo's existing convention) opens above yesterday's high
and reverses down through it. Economic rationale (source's own): a gap that
opens beyond the PRIOR day's extreme signals an overreaction/panic move at
the open; if price then reverses back through that same extreme level
intraday, it signals the gap was an emotional overshoot rather than genuine
new information, and the reversal captures the overreaction's unwind.

Daily-bar adaptation (this repo's OHLCV granularity is daily, not intraday,
so entry/exit are evaluated at the close of the SAME bar rather than an
intraday buy-stop fill, following this repo's existing convention for
similar single-day gap/reversal patterns, e.g.
strategies/2026-09-08_gap_fill_ibs_gated.py and the Bullish Kicker pattern
2026-09-06-155): buy signal fires when TODAY's open is below YESTERDAY's
low (the gap-down condition) AND today's close recovers back above
yesterday's low (the "reverses upward and breaks through" confirmation).
Exit: source's own disclosed rule ("positions are force-closed at the end
of the session" per the TradingView script snippet, i.e. it's designed as
a single-day trade) is adapted here as a fixed 1-3 day hold
(`max_hold_days`) since force-closing literally same-day isn't meaningful
on daily bars (entry IS the close).

First "Oops!" pattern strategy in this repo -- zero prior matches for
"OOPS"/"Oops" in strategies_index.jsonl.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position series)
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
    max_hold_days: int = 2,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Buy signal: today's open < yesterday's low (gap down beyond prior
    day's extreme) AND today's close > yesterday's low (price reverses
    back up through that level by the close, confirming the "Oops!"
    overreaction-unwind). Holds for `max_hold_days` trading days (source's
    own single-day force-close rule, extended to a short fixed hold since
    this repo's daily-bar granularity makes same-day exit meaningless).
    """
    df = _prep(price_df)
    open_ = df["open"]
    close = df["close"]
    low = df["low"]

    prior_low = low.shift(1)
    gap_down = open_ < prior_low
    reversal_confirmed = close > prior_low
    buy_signal = (gap_down & reversal_confirmed).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(buy_signal.iloc[i]):
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
