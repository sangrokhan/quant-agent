"""Strategy: RSI Cross swing-detection entry with fixed-bar time exit.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-143):
Domenico D'Errico's "Detecting Swings" (TASC May 2017) presents four
swing-detection methods feeding one shared TradeStation strategy shell
(pivot, Bollinger, RSI-cross, RSI+higher-low/lower-high). This strategy
implements swing method #3 ("RSI Cross") long-only: a short RSI(5) crossing
UP through an oversold-adjacent threshold (40, not the classic 30) signals
that a swing low has just formed and momentum is turning up; there is no
long-term trend filter (the source's own shell trades either direction with
no separate regime gate) and no explicit oversold/overbought "extreme"
target exit -- the source's own strategy shell exits every position
unconditionally after NumberOfBarsToExit (=4) bars, a pure time-stop, which
is what actually differentiates this from every already-tried
RSI-threshold-crossover strategy in this repo (2026-09-04-077 uses a
55/45 momentum-continuation crossover with no time-stop; 2026-09-04-161
combines RSI(14) recovery with MACD and a *max_hold_days* time-stop but only
as a secondary exit alongside RSI>70; none use a *forced, unconditional*
n-bar time exit as the strategy's ONLY exit condition with a short-period
RSI(5) and non-standard 40 threshold). Source:
https://traders.com/Documentation/FEEDbk_docs/2017/05/TradersTips.html
(read via browser_exec, unvisited TASC archive month).

Signal logic
------------
- RSI(rsi_length) computed on close (Wilder-style, via EMA smoothing of
  gains/losses -- standard construction).
- Entry (long): RSI crosses UP over `entry_threshold` (default 40, per the
  source's own RSIOverSold=40 default).
- Exit: unconditional after `hold_bars` (default 4) trading days from entry
  -- the source's own `NumberOfBarsToExit` mechanic, i.e. a pure time-stop
  with no price/indicator exit condition at all.
- Flat otherwise; no shorting (long-only per SAFETY.md, source's own
  SellShort branch dropped).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _rsi(close: pd.Series, length: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.fillna(50.0)
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    rsi_length: int = 5,
    entry_threshold: float = 40.0,
    hold_bars: int = 4,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rsi = _rsi(close, rsi_length)
    cross_up = (rsi > entry_threshold) & (rsi.shift(1) <= entry_threshold)

    position = pd.Series(0, index=close.index, dtype=int)
    bars_left = 0
    for i in range(len(close)):
        if bars_left > 0:
            position.iloc[i] = 1
            bars_left -= 1
        elif cross_up.iloc[i]:
            position.iloc[i] = 1
            bars_left = hold_bars - 1
        else:
            position.iloc[i] = 0

    return position


def generate_returns(
    price_df: pd.DataFrame,
    rsi_length: int = 5,
    entry_threshold: float = 40.0,
    hold_bars: int = 4,
) -> pd.Series:
    """Return the strategy's daily return series (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]

    position = generate_signals(
        price_df,
        rsi_length=rsi_length,
        entry_threshold=entry_threshold,
        hold_bars=hold_bars,
    )
    daily_ret = close.pct_change().fillna(0.0)
    strat_ret = position.shift(1).fillna(0) * daily_ret
    return strat_ret
