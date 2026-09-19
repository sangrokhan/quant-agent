"""Strategy: 52-Week High breakout, exit on 200-day SMA cross (Exit 1 variant).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-054):
Per quantifiedstrategies.com's "52-Week High Trading Strategy" article
(https://www.quantifiedstrategies.com/52-week-high-strategy/, visited this
iteration via browser_exec fallback -- web_search DDGS backend hit repeated
TLS/connection-reset errors on every query attempted), the "52-week high
effect" documents that stocks/assets trading at or near their 52-week
(252-trading-day) high tend to outperform going forward -- momentum/
underreaction to good news near a psychologically salient reference point,
per academic work the source cites (Hong/Jordan/Liu "Industry Information
and the 52-Week High Effect", George/Hwang 52-week-high momentum).

The source summarizes a fully disclosed single-asset backtest from
enlightenedstocktrading.com ("Should you trade with a stocks 52-week highs
or lows?"): buy when a stock closes at a new 52-week high, and test three
exit rules. This repo implements Exit 1 (the source's own best-performing
exit, 8.6% CAGR / 44% MDD in its original stock-universe backtest): "Hold
until the stock crosses below the 200-day moving average." This is the
plain single-asset momentum-breakout-then-trend-exit construction, directly
implementable under this repo's generate_signals/generate_returns contract
(unlike the source's other two backtests, which use cross-sectional
top-10-stock-basket ranking and monthly rebalancing across S&P 100
constituents -- feasibility-blocked here since this repo's loaders/strategy
interface are single-symbol only, same blocker noted for prior
cross-sectional-rotation attempts in this repo, e.g. 2026-09-11-037).

Mechanical rules:
  1. Entry (long): close makes a new `lookback_days`-day (default 252,
     approximating 52 weeks) high (today's close >= rolling max close over
     the trailing lookback_days, excluding today via shift so it's a
     genuine "new high" breakout signal known at the close).
  2. Exit: close crosses below its own SMA(exit_sma_window) (default 200,
     the source's disclosed "Exit 1"), or a max_hold_days time-stop as a
     repo-standard safety valve against indefinite single-asset holds
     (the source's original version has no time-stop since it trades a
     rotating basket of stocks; a single-asset adaptation needs one to
     avoid pathological infinite-hold cases).
  3. Flat otherwise.

First 52-Week-High strategy in this repo (0 prior "52 Week High" entries in
strategies_index.jsonl as of this iteration); distinct from all prior
Donchian-channel/breakout-family entries (which use a fixed N-day
high/low channel breakout+reverse construction, not a single-direction
"new high -> trend-following exit" momentum-continuation rule) and from
all prior 200-day-SMA trend-filter entries (which gate a *different*
indicator's entry, not use the 200SMA purely as an exit for a 52-week-high
breakout entry).

Source: https://www.quantifiedstrategies.com/52-week-high-strategy/ (the
site's own individual-stock/S&P-100 Amibroker backtest code is paywalled;
we implement its plainly disclosed rule -- buy 52wk high, exit below
200d SMA -- directly, not a reproduction of the paywalled code).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (position: 1 long/0 flat)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
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
    lookback_days: int = 252,
    exit_sma_window: int = 200,
    max_hold_days: int = 500,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    # "New 52-week high" = today's close is the highest close over the
    # trailing lookback_days INCLUDING today.
    rolling_high = close.rolling(lookback_days, min_periods=lookback_days).max()
    is_new_high = close >= rolling_high

    sma = close.rolling(exit_sma_window).mean()
    exit_below_sma = close < sma

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_below_sma.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(is_new_high.iloc[i]):
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
