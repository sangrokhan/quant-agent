"""Strategy: ROC "crash" dip-buy with fixed-N-day time-stop exit.

Hypothesis (see knowledge_base/strategies_log.jsonl for this entry's id):
Per QuantifiedStrategies.com's "Bitcoin Crash Trading Strategy: Backtest
Analysis" (https://www.quantifiedstrategies.com/bitcoin-crash-trading-strategy/,
visited this iteration), the source's own disclosed mechanical rule is:
    - Compute ROC(N) = pct change in close over the last N trading days.
    - If ROC(N) <= -roc_drop_pct (a sharp N-day decline), go long at the
      close.
    - Exit at the close after N days (same N used for both the ROC lookback
      and the exit hold length).

The source's own optimization grid was ROC drop in {5%,10%,...,25%} and
N in {10,20,...,100} days, tested on Bitcoin only, and explicitly reported
"erratic" / "not tradable" full-sample results with few, random-looking
clusters of good performance -- an important prior to weigh when deciding
accept/reject here. This iteration re-implements the same disclosed rule
generically (source symbol-agnostic) and tests it across both equity and
crypto per this repo's standard grid protocol, rather than trusting the
source's own (candidly skeptical) single-asset conclusion.

Signal logic
------------
- roc_pct = 100 * (close / close.shift(roc_window) - 1)
- Entry (long): roc_pct <= -roc_drop_pct (an N-day decline of at least
  roc_drop_pct%).
- Exit: after exactly `roc_window` trading days held (fixed time-stop,
  matching the source's own rule of using the same N for lookback and
  exit).
- Flat otherwise. No re-entry while already in a position (avoids pyramiding
  into further declines).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
        Given an OHLCV DataFrame (columns: timestamp, open, high, low,
        close, volume; as returned by data/loaders.py), returns the
        strategy's daily return series (position-weighted, no transaction
        costs applied here -- that's handled separately by
        check_transaction_cost_survival).

    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
        Returns a {0, 1} position series aligned to price_df.index
        (1 = long, 0 = flat).
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
    roc_window: int = 20,
    roc_drop_pct: float = 15.0,
) -> pd.Series:
    """Return a {0,1} position series: long after an N-day crash, held for N days."""
    df = _prep(price_df)
    close = df["close"]

    roc_pct = 100.0 * (close / close.shift(roc_window) - 1.0)
    crash_trigger = roc_pct <= -roc_drop_pct

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    hold_bars_left = 0

    trigger_arr = crash_trigger.to_numpy()
    pos_arr = position.to_numpy().copy()

    for i in range(len(close)):
        if in_position:
            hold_bars_left -= 1
            pos_arr[i] = 1
            if hold_bars_left <= 0:
                in_position = False
        else:
            if bool(trigger_arr[i]):
                in_position = True
                hold_bars_left = roc_window
                pos_arr[i] = 1

    position = pd.Series(pos_arr, index=close.index, dtype=int)
    return position


def generate_returns(
    price_df: pd.DataFrame,
    roc_window: int = 20,
    roc_drop_pct: float = 15.0,
) -> pd.Series:
    """Daily strategy returns: prior day's position * that day's close-to-close return."""
    df = _prep(price_df)
    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)

    position = generate_signals(price_df, roc_window=roc_window, roc_drop_pct=roc_drop_pct)
    # Position decided at close of day t is held for return realized on day t+1.
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
