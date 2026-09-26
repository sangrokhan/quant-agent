"""Strategy: "Classical" IBS + RSI(21) mean reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-26-009):
QuantifiedStrategies.com's "S&P 500 Mean Reversion Using IBS and RSI:
Classical Approach" (https://quantifiedstrategies.substack.com/p/s-and-p-500-mean-reversion-using-541,
snippet-disclosed trading rule -- full article paywalled, but the rule
itself is quoted verbatim in the public search-result description):

  1. IBS (Internal Bar Strength) = (Close-Low)/(High-Low) must be below
     ibs_threshold (source default 0.25).
  2. RSI(rsi_window) (source default 21-period) must be below
     rsi_threshold (source default 45).
  3. If both 1 and 2 are true simultaneously, go long at today's close.
  4. Exit when close is higher than yesterday's close (next-up-close exit).

This is distinct from every other IBS-family entry in this repo: prior IBS
strategies pair IBS with RSI(2)/RSI(3)/RSI(5) fast oscillators or SMA(200)
trend filters (2026-09-04-089, 2026-09-20-082, etc); none use a slow
RSI(21) confirmation with NO trend filter and a same-length-1 next-up-close
exit as the sole exit rule. Added a max_hold_days safety exit (source's
own rule has no explicit time-stop, so an unbounded hold could occur in a
persistent downtrend -- this repo's established pattern of adding a
time-stop safety net per RESEARCH_LOOP.md Step 5 guidance).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
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
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0.0, 1e-12)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    ibs_threshold: float = 0.25,
    rsi_window: int = 21,
    rsi_threshold: float = 45.0,
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    high = df["high"]
    low = df["low"]

    rng = (high - low).replace(0.0, 1e-12)
    ibs = (close - low) / rng
    rsi = _rsi(close, rsi_window)

    entry = (ibs < ibs_threshold) & (rsi < rsi_threshold)
    exit_up_close = close > close.shift(1)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_up_close.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry.iloc[i].item() if hasattr(entry.iloc[i], "item") else entry.iloc[i]):
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
