"""Strategy: Ultimate Oscillator (Larry Williams) threshold-cross mean-reversion.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-050):
Per Google AI-overview + QuantifiedStrategies.com's own backtested rule:
the Ultimate Oscillator (UO, Larry Williams) blends buying pressure vs
true range across 3 timeframes (7, 14, 28-period, weighted 4:2:1) into a
single 0-100 oscillator. QuantifiedStrategies' own simpler, concretely
backtested rule (rather than the more elaborate/subjective divergence
variant, which has the same swing-detection implementability issue as
the already-rejected RSI-divergence strategy, 2026-09-03-019): buy when
UO crosses below a low threshold (40), sell/exit when UO crosses above a
high threshold (50). Long-only, per repo convention.

Ultimate Oscillator formula (standard, Williams):
    BP (Buying Pressure) = close - min(low, prev_close)
    TR (True Range) = max(high, prev_close) - min(low, prev_close)
    Avg_n = sum(BP, n) / sum(TR, n)   for n in {7, 14, 28}
    UO = 100 * (4*Avg_7 + 2*Avg_14 + 1*Avg_28) / (4 + 2 + 1)

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


def _ultimate_oscillator(
    df: pd.DataFrame,
    w1: int = 7,
    w2: int = 14,
    w3: int = 28,
) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)

    bp = close - pd.concat([low, prev_close], axis=1).min(axis=1)
    tr = pd.concat([high, prev_close], axis=1).max(axis=1) - \
         pd.concat([low, prev_close], axis=1).min(axis=1)

    def avg(n: int) -> pd.Series:
        return bp.rolling(n).sum() / tr.rolling(n).sum().replace(0, pd.NA)

    avg1, avg2, avg3 = avg(w1), avg(w2), avg(w3)
    uo = 100 * (4 * avg1 + 2 * avg2 + 1 * avg3) / 7.0
    return uo


def generate_signals(
    price_df: pd.DataFrame,
    buy_threshold: float = 40.0,
    sell_threshold: float = 50.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    uo = _ultimate_oscillator(df)

    buy_cross = (uo < buy_threshold) & (uo.shift(1) >= buy_threshold)
    sell_cross = (uo > sell_threshold) & (uo.shift(1) <= sell_threshold)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(sell_cross.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(buy_cross.fillna(False).iloc[i]):
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
