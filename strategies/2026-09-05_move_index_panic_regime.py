"""Strategy: MOVE index (bond volatility) panic-spike regime filter.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-043):
The ICE BofA MOVE Index measures implied volatility of US Treasury rates via
the options market -- the bond-market analog of the VIX. Per Google's
AI-overview synthesis (citing TradingView scripts) of MOVE-index/TLT
trading rules: a MOVE spike above 150 signals bond options aggressively
pricing panic/yield-curve shocks, leaving Treasuries oversold and primed
for a safe-haven rebound (buy signal); MOVE dropping below 100 signals
uncertainty fading (exit to cash, locking in gains before a slow bond
bear market resumes); the source also recommends a trend-filter
enhancement -- only execute the buy signal if the traded asset is above
its own 200-day SMA (avoid catching falling knives during structural
rate-hike regimes). Implemented here with the standard trend-follow-plus-
regime-trigger pattern used elsewhere in this repo (e.g. DXY 50-SMA filter
2026-09-05-026): position stays flat by default; a MOVE panic-spike above
`move_high_threshold` (with price already above its own 200d SMA) triggers
a long entry that holds until MOVE drops below `move_low_threshold`
(exit/take-profit) or a max_hold_days time-stop backstop. First MOVE-index
strategy in this repo -- distinct from all prior VIX-based strategies
(2026-09-04-103, 2026-09-04-157, 2026-09-05-021, 2026-09-05-028), which
measure EQUITY option-implied volatility rather than bond/rates volatility.
Tested on both equity (QQQ, SPY, per the source's own TLT-safe-haven logic
translated to broad equities) and crypto (BTC/USDT, ETH/USDT, falsification
check -- no theoretical link between bond-rate panic and crypto expected).

Signal logic
------------
- Fetch ^MOVE daily closes via data/loaders.py load_equity("^MOVE", ...)
  internally (mirrors the DXY/HYG-LQD strategies' cross-asset-signal
  pattern for data not present in price_df itself).
- Entry (long): MOVE crosses above `move_high_threshold` (default 150,
  "panic zone") AND close > its own 200d SMA (trend filter, avoids
  buying into a structural downtrend).
- Exit: MOVE drops below `move_low_threshold` (default 100, "calm zone"),
  OR a max_hold_days time-stop backstop.
- Flat otherwise (long-only; no short leg per SAFETY.md scope).

Interface contract for validators (see validation/validators.py) and grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
"""

from __future__ import annotations

import sys
import os

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _get_move_series(idx: pd.DatetimeIndex) -> pd.Series:
    """Fetch ^MOVE closes, reindexed/ffilled onto the strategy's own trading-day index."""
    from loaders import load_equity

    start = (idx.min() - pd.Timedelta(days=30)).to_pydatetime()
    end = (idx.max() + pd.Timedelta(days=5)).to_pydatetime()

    move = load_equity("^MOVE", start, end).set_index("timestamp")["close"].sort_index()
    move.index = move.index.tz_localize(None) if move.index.tz is not None else move.index

    target_idx = idx.tz_localize(None) if getattr(idx, "tz", None) is not None else idx
    move = move.reindex(move.index.union(target_idx)).sort_index().ffill()
    move = move.reindex(target_idx)
    move.index = idx
    return move


def generate_signals(
    price_df: pd.DataFrame,
    move_high_threshold: float = 150.0,
    move_low_threshold: float = 100.0,
    trend_window: int = 200,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    idx = df.index

    try:
        move = _get_move_series(idx)
    except Exception:
        return pd.Series(0, index=idx, dtype=int)

    trend_sma = close.rolling(trend_window).mean()
    trend_ok = close > trend_sma

    entry = (move > move_high_threshold) & trend_ok.fillna(False)
    exit_signal = move < move_low_threshold

    position = pd.Series(0, index=idx, dtype=int)
    in_pos = False
    hold_count = 0
    for i in range(len(idx)):
        if pd.isna(move.iloc[i]) or pd.isna(trend_sma.iloc[i]):
            position.iloc[i] = 1 if in_pos else 0
            continue
        if in_pos:
            hold_count += 1
            if exit_signal.iloc[i] or hold_count >= max_hold_days:
                in_pos = False
                hold_count = 0
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if entry.iloc[i]:
                in_pos = True
                hold_count = 0
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
