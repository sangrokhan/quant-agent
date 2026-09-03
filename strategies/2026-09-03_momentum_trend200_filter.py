"""Strategy: Trend-filtered absolute momentum (long-term SMA gate + medium-term momentum).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-03-004), sourced from
https://github.com/IsaacDodds/crypto-momentum-backtest (README findings on a
cross-sectional crypto momentum backtest, 2021-2026): the source found that
adding a 200-day trend filter (only deploy capital when price/BTC is above its
200-day SMA) roughly HALVED max drawdown versus an unfiltered momentum
strategy (v1 MDD -89.8% -> v2 MDD -53.8%), at some cost to raw return/Sharpe.
The prior in-repo attempts at pure absolute momentum on BTC/USDT
(2026-09-03-002: 90d lookback, MDD 66.0%; 2026-09-03-003: 45d lookback +
vol-targeting overlay, MDD 47.6%) both failed the 35% MDD hard risk gate.
This strategy tests whether ANDing a strict long-horizon (200-day) SMA trend
filter on top of a shorter/medium momentum signal -- rather than vol-target
position sizing -- gets max drawdown under the 35% budget while retaining a
Sharpe >= 1.0, on BOTH equity and crypto (the source only tested crypto).

Signal logic
------------
- Trend gate: close > SMA(trend_window) (long-term regime filter, default 200d).
- Momentum signal: trailing mom_window-day return > 0 (medium-term absolute
  momentum, default 60d).
- Long only when BOTH conditions hold; flat otherwise (no shorting).

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
    mom_window: int = 60,
    trend_window: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    trailing_return = close.pct_change(mom_window)
    trend_sma = close.rolling(trend_window).mean()

    momentum_positive = trailing_return > 0
    above_trend = close > trend_sma

    position = (momentum_positive & above_trend).fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    # Shift position by 1 day: yesterday's signal determines today's exposure
    # (avoid look-ahead bias -- can't trade on today's own close).
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
