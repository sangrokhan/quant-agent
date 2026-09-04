"""Strategy: Santa Claus Rally calendar effect.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-008),
sourced from Wikipedia/Britannica (Stock Trader's Almanac-popularized
pattern) and corroborated by quantifiedstrategies.com's own backtest
headline (CAGR ~0.7% while only invested ~2.3% of the time): US equities
tend to rally during a narrow ~7-trading-day window spanning the last 5
trading days of December and the first 2 trading days of January -- widely
attributed to holiday-season optimism, light institutional trading volume,
and window-dressing/January-effect anticipatory buying.

This is a long-only, purely calendar-based (not price-based) strategy --
distinct from the already-tested broader Halloween/Sell-in-May seasonal
strategy (2026-09-04-104, a 6-month Nov-Apr hold window) since this is a
much narrower ~7-trading-day annual window concentrated at the December/
January boundary specifically, not a broad-season hold. Tested here on
both equity (where the mechanism plausibly applies) and crypto (where it
plausibly should NOT, since there's no institutional light-volume/
window-dressing effect specific to BTC/ETH) as an explicit cross-asset-class
falsification check, following the same pattern as the turn-of-month and
Halloween-effect strategies already in this repo.

Interface contract for validators (see validation/validators.py) and grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns,
        position lagged by 1 day to avoid look-ahead bias)
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
    december_trading_days: int = 5,
    january_trading_days: int = 2,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Long during the last `december_trading_days` trading days of December
    AND the first `january_trading_days` trading days of January (the
    classic Santa Claus Rally window is december_trading_days=5,
    january_trading_days=2); flat on all other trading days.
    """
    df = _prep(price_df)
    idx = df.index
    ym = pd.Series(idx.year * 100 + idx.month, index=idx)

    rank_from_start = ym.groupby(ym).cumcount()
    rank_from_end = ym.groupby(ym).cumcount(ascending=False)

    is_december = idx.month == 12
    is_january = idx.month == 1

    late_december = is_december & (rank_from_end.values < december_trading_days)
    early_january = is_january & (rank_from_start.values < january_trading_days)

    position = pd.Series((late_december | early_january).astype(int), index=idx)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
