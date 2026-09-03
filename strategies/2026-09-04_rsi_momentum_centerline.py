"""Strategy: RSI as a MOMENTUM (centerline-cross) signal, not mean-reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-077):
Per QuantifiedStrategies.com's Bitcoin RSI trading article: RSI used as a
classic MEAN-REVERSION indicator (buy oversold, sell overbought) is
"basically worthless" on Bitcoin/crypto in the source's own optimization
sweep, but RSI used as a MOMENTUM indicator (buy when RSI crosses ABOVE an
upper threshold near the centerline, sell when it crosses back below a
lower threshold) performed "much better" -- best results clustered around
a short RSI period (RSI(5)). Every prior RSI variant tested in this repo
(RSI2 -005, RSI-divergence -019) bets on RSI extremes reverting; this
instead treats a rising RSI crossing above the centerline as a
trend-continuation entry, analogous in spirit to the MACD/ROC/Vortex
zero-line-cross strategies already tested but built on RSI's bounded 0-100
scale instead. Directly testable on this repo's crypto pairs as the
source's own primary claimed use case.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly).
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
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def generate_signals(
    price_df: pd.DataFrame,
    rsi_window: int = 5,
    entry_threshold: float = 55.0,
    exit_threshold: float = 45.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Entry: RSI crosses above ``entry_threshold`` (momentum building).
    Exit: RSI crosses below ``exit_threshold`` (momentum fading).
    """
    df = _prep(price_df)
    close = df["close"]
    rsi = _rsi(close, rsi_window)

    cross_up = (rsi > entry_threshold) & (rsi.shift(1) <= entry_threshold)
    cross_down = (rsi < exit_threshold) & (rsi.shift(1) >= exit_threshold)

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    for i in range(len(df)):
        if in_position:
            if bool(cross_down.iloc[i]) if not pd.isna(cross_down.iloc[i]) else False:
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(cross_up.iloc[i]) if not pd.isna(cross_up.iloc[i]) else False:
                in_position = True
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
