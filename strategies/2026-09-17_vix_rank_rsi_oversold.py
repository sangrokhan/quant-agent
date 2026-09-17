"""Strategy: RSI(14) oversold entry gated by a VIX Rank (percentile) filter,
fixed profit target / time-stop exit, no stop-loss.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-17-183):
Per an options.cafe blog backtest (https://options.cafe/blog/momentum-rsi-strategy-backtest-results/,
read this iteration via browser_exec) replicating a viral r/algotrading post
("Algo Update - 81.6% Win Rate...", u/jabberw0ckee): the original post's
cross-sectional momentum-universe-selection component is not adaptable to
this repo's single-symbol generate_returns_fn contract, but the
independent replication article's own "key innovation" -- a VIX RANK
filter (current VIX's PERCENTILE RANK within its own trailing 365-day
window, distinct from a VIX/SMA ratio or VIX Bollinger-Band breakout
already tested in this repo) -- is a standalone, single-symbol-adaptable
mechanism. This strategy tests that core mechanism directly on the index
itself: RSI(14) crossing below 30 (oversold) while VIX Rank <= 70 (i.e.
NOT in an extreme-fear/high-vol-percentile regime -- counterintuitively,
the source's own optimization found FILTERING OUT the highest-VIX-percentile
regime, not seeking it, improved risk-adjusted returns) triggers a long
entry; exit at a fixed 3% profit target or after a 10-day time-stop
(source's own exact numbers), with no stop-loss (source's own explicit
choice). First VIX-RANK-(percentile)-based filter in this repo -- distinct
from CVR3 (VIX vs its own 10d SMA, extension-based), Connors VIX-RSI
(RSI computed ON the VIX series), and VIX/VIX3M term-structure strategies
already tested here.

Signal logic
------------
- RSI(14) via Wilder's standard smoothing.
- VIX Rank = percentile rank of today's VIX close within the trailing
  365-calendar-day (rank_window) window of VIX closes (0-100 scale).
- Entry (long): RSI(14) crosses from >=30 to <30 (fresh oversold
  cross, not just "RSI is below 30" every bar) AND VIX Rank <=
  max_vix_rank (source's own 70 default).
- Exit: close >= entry_price * (1 + profit_target_pct), OR
  max_hold_days elapsed, whichever comes first. No stop-loss (matches
  source exactly).
- Flat otherwise; long-only, single position at a time.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly). Since this strategy
needs the VIX series (a second instrument) alongside the primary
price_df, it fetches ^VIX internally via data/loaders.py's load_equity
(matching this repo's established pattern for VIX-dependent strategies,
e.g. strategies/2026-09-05_cvr3_vix_market_timing.py-style modules).
"""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
from loaders import load_equity  # noqa: E402


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
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _vix_rank(index: pd.DatetimeIndex, rank_window: int) -> pd.Series:
    start = index[0] - pd.Timedelta(days=rank_window + 30)
    end = index[-1] + pd.Timedelta(days=5)
    vix_df = load_equity("^VIX", start, end)
    vix_df = _prep(vix_df)
    vix_close = vix_df["close"].reindex(index, method="ffill")
    rank = vix_close.rolling(rank_window, min_periods=max(30, rank_window // 4)).apply(
        lambda w: (w <= w.iloc[-1]).sum() / len(w) * 100.0, raw=False
    )
    return rank


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 14,
    rsi_threshold: float = 30.0,
    max_vix_rank: float = 70.0,
    rank_window: int = 365,
    profit_target_pct: float = 0.03,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    rsi = _rsi(close, rsi_window)
    vix_rank = _vix_rank(df.index, rank_window)

    oversold_cross = (rsi < rsi_threshold) & (rsi.shift(1) >= rsi_threshold)
    vix_ok = (vix_rank <= max_vix_rank).fillna(False)
    entry = (oversold_cross & vix_ok).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    hold_days = 0
    entry_price = None

    for i in range(n):
        px_close = close.iloc[i]

        if in_position:
            hold_days += 1
            target_hit = px_close >= entry_price * (1 + profit_target_pct)
            if target_hit or hold_days >= max_hold_days:
                in_position = False
                entry_price = None
                hold_days = 0
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
            continue

        if bool(entry.iloc[i]):
            in_position = True
            entry_price = px_close
            hold_days = 0
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
