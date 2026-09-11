"""Strategy: New-high-but-weak-close (Donchian high + low IBS) contrarian long.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-11-114):
Per quantifiedstrategies.com's "5 Algorithmic Trading Strategies 2026"
(https://www.quantifiedstrategies.com/algorithmic-trading-strategies/,
"Strategy #5"), the source's own disclosed SPY backtest rule: "Today's
high must be higher than the high of the last ten days, and the IBS
indicator must be below 0.15. If both are true, we buy the close... We
sell when the close is higher than yesterday's high." Source reports (SPY,
1993-2026): 185 trades, avg gain 0.6%/trade, ~8% time invested, 3.2%
annualized, 8% max drawdown (their lowest-drawdown strategy of the five
presented).

This is a genuinely contrarian construction distinct from every other
IBS-family strategy already in this repo: prior IBS entries all condition
on price WEAKNESS (a new LOW, a breakdown, or a low absolute IBS combined
with a downside price signal). Here the price signal is bullish (a new
`donchian_window`-day HIGH was made intraday), but the IBS filter still
requires the day close weakly (near its low) despite making that high --
i.e. an intraday reversal/failed-follow-through pattern, betting that the
weak close after a strong intraday high still resolves upward the next
session(s).

Signal logic
------------
- Entry (long), on close: today's high > rolling max of the prior
  `donchian_window` days' highs (a new N-day high made intraday) AND
  IBS = (close-low)/(high-low) < `ibs_threshold` (close near the day's low
  despite the new high).
- Exit: close > yesterday's high (source's own exit trigger: "sell on
  strength"), OR a `max_hold_days` time-stop (added robustness safety net,
  not in the original source, consistent with this repo's convention).
- Flat otherwise, long-only.

Interface contract (validation/grid_test.py, validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} positions)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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
    donchian_window: int = 10,
    ibs_threshold: float = 0.15,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    range_hl = (high - low).replace(0, float("nan"))
    ibs = (close - low) / range_hl
    ibs = ibs.astype(float)

    prior_n_high = high.shift(1).rolling(donchian_window).max()
    new_high = high > prior_n_high
    weak_close = ibs < ibs_threshold

    entry = (new_high & weak_close.fillna(False)).fillna(False)
    prior_high = high.shift(1)
    exit_strength = close > prior_high

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_strength.iloc[i]) or held >= max_hold_days:
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
