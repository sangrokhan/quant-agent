"""Strategy: Unfilled Gap-Down + RSI(10)<50 fixed-holding-period swing.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-084):
Per QuantifiedStrategies.com's "Unfilled Gap Trading Strategies" article
(https://www.quantifiedstrategies.com/unfilled-gap-trading-strategies/,
visited this iteration), the source defines an "unfilled gap down" as a
day where today's HIGH never trades back up into yesterday's range (i.e.
today's high < yesterday's low) -- a stricter definition than a simple
open-vs-prior-close gap threshold used by every other gap strategy in
this repo. The source's own ES-futures study (Aug 2010-Aug 2021) found
133 unfilled gap-downs (~5% of bars), with only 63% filling within 5 days
(i.e. a meaningful minority persist unfilled longer). The source's own
disclosed refinement: entering at the CLOSE of the unfilled-gap-down day
and exiting x days later at the close is more profitable when GATED by a
10-day RSI filter -- specifically, "the best gaps down happen when the
RSI value is below 50" -- which also raises the average gain per trade
and profit factor versus the unfiltered version.

This is distinct from every prior gap strategy in this repo: (1) it uses
the source's own stricter "unfilled" gap DEFINITION (high < yesterday's
low, not a same-day open-vs-close percentage threshold); (2) it enters at
the CLOSE of the gap day itself (not the open, unlike 2026-09-08-171's
multi-day-fill or -016's IBS+RSI(5) open-entry swing); (3) it uses a FIXED
x-day holding period with no signal-based early exit (source's own
disclosed backtest methodology), rather than "hold until gap fills" logic;
(4) the RSI filter threshold is RSI(10)<50 specifically (not RSI(5) or
IBS composite as in prior gap strategies).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 10,
    rsi_threshold: float = 50.0,
    hold_days: int = 5,
) -> pd.Series:
    """Return a {0,1} long/flat position series: enter long at the close
    of an "unfilled gap down" day (today's high < yesterday's low) with
    RSI(rsi_window) on that day < rsi_threshold, hold for exactly
    hold_days trading days (fixed time-stop, no early exit -- per the
    source's own disclosed backtest methodology), no re-entry while
    already in a position."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    unfilled_gap_down = high < low.shift(1)
    rsi = _rsi(close, rsi_window)
    entry_signal = (unfilled_gap_down & (rsi < rsi_threshold)).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    hold_counter = 0
    for i in range(len(close)):
        if in_position:
            hold_counter += 1
            if hold_counter >= hold_days:
                in_position = False
                position.iloc[i] = 1  # still held through this day's close per fixed-hold rule
                hold_counter = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry_signal.iloc[i]):
                in_position = True
                hold_counter = 0
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
    strategy_ret = position.shift(1).fillna(0).astype(float) * daily_ret
    return strategy_ret
