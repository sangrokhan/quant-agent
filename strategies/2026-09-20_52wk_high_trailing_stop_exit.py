"""Strategy: 52-Week High breakout, trailing-stop exit (source's "Exit 2").

Direct follow-up to prior id 2026-09-20-054 (52-Week High breakout +
200d-SMA-exit, near-miss REJECTED: SPY Sharpe 0.879, QQQ Sharpe 0.880) and
2026-09-20-055 (low-vol-gate rescue attempt, REJECTED, made things WORSE,
Sharpe dropped to 0.56 -- documented negative result, do not retry that
approach). This iteration instead tries the OTHER rescue direction that
2026-09-20-054's own notes flagged: the source article
(https://www.quantifiedstrategies.com/52-week-high-strategy/) disclosed
THREE exit variants in its cited enlightenedstocktrading.com backtest:
"Exit 1" (200d SMA cross, already tested, near-miss), "Exit 2" (25%
trailing stop loss), and "Exit 3" (100-bar lowest close). This sub-
iteration implements Exit 2: hold a 52-week-high breakout position with a
trailing stop set trail_pct below the running peak close since entry;
exit when price closes below that trailing stop level, or a max_hold_days
safety time-stop. No new external research this sub-iteration (same
source, its second disclosed exit rule).

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
    trail_pct: float = 0.25,
    max_hold_days: int = 500,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    rolling_high = close.rolling(lookback_days, min_periods=lookback_days).max()
    is_new_high = close >= rolling_high

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    peak_since_entry = 0.0
    for i in range(len(close)):
        c = float(close.iloc[i])
        if in_position:
            held = i - entry_idx
            peak_since_entry = max(peak_since_entry, c)
            trail_stop_level = peak_since_entry * (1.0 - trail_pct)
            if c < trail_stop_level or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(is_new_high.iloc[i]):
                in_position = True
                entry_idx = i
                peak_since_entry = c
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
