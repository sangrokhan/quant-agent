"""Strategy: Overnight-return premium + trend filter, excluding Friday->Monday weekend holds.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-08-054):
Direct follow-up to accepted 2026-09-08-053 (unconditional overnight-return +
trend-filter strategy, Sharpe 1.45 QQQ / 1.43 SPY). Per Investopedia's
"Weekend Effect" (Frank Cross 1973): stock returns tend to be lower on
Mondays than the preceding Friday -- the weekend gap (Friday close to Monday
open, ~2.5 days of information accumulation vs ~16-18 hours for a normal
weekday overnight gap) may carry a systematically worse risk/return profile
than weekday-only overnight holds. This strategy tests whether EXCLUDING the
Friday->Monday weekend overnight hold (staying flat over the weekend,
keeping the same trend-filter-gated weekday overnight holds otherwise)
improves on -053's already-strong unconditional-per-weekday result -- i.e.
does the weekend effect meaningfully hurt this strategy, or was -053's
strength already robust to it?

Signal logic
------------
- Identical trend-filter-gated overnight-return construction as -053
  (close[t-1] > SMA(trend_window) as of t-1 -> hold overnight into bar t's
  open), EXCEPT the position is forced to 0 whenever the entry day is a
  Monday (i.e. the prior close was a Friday -- excludes the weekend gap
  specifically) if exclude_weekend_gap=True.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df: pd.DataFrame, **params) -> pd.Series
    generate_signals(price_df: pd.DataFrame, **params) -> pd.Series
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
    trend_window: int = 100,
    exclude_weekend_gap: bool = True,
) -> pd.Series:
    """Return a {0,1} series: 1 = holding overnight into this bar's open."""
    df = _prep(price_df)
    close = df["close"]

    sma = close.rolling(trend_window).mean()
    trend_up = close > sma
    position = trend_up.shift(1).fillna(False).astype(int)

    if exclude_weekend_gap:
        is_monday = pd.Series(close.index.dayofweek == 0, index=close.index)
        position = position.where(~is_monday, 0)

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Overnight-only daily returns: open[t]/close[t-1] - 1, gated by trend filter
    and (optionally) excluding the Friday->Monday weekend gap."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]

    position = generate_signals(price_df, **kwargs)
    overnight_ret = (open_ / close.shift(1) - 1.0).fillna(0.0)
    strategy_ret = position * overnight_ret
    return strategy_ret
