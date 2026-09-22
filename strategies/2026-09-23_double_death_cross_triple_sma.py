"""Strategy: Double Death Cross -- 50/100/200-day SMA triple-confirmation trend filter.

Hypothesis (see knowledge_base/strategies_log.jsonl, this iteration's id):
Per QuantifiedStrategies.com's "Does the Death Cross Actually Work?
Backtesting 65 Years of Trading Data"
(https://www.quantifiedstrategies.com/death-cross-in-trading/), the classic
Death Cross (50-day SMA crosses below 200-day SMA) as an exit signal +
Golden Cross (50-day SMA crosses back above 200-day SMA) as a re-entry
signal produces buy-and-hold-like returns with meaningfully reduced
drawdowns, but is prone to false signals (e.g. the March 2020 COVID
whipsaw, which triggered exit near the exact bottom). The source explicitly
discloses an enhancement it calls the "Double Death Cross": add a 100-day
SMA as a THIRD confirmation layer, requiring the 50-day SMA to be below
BOTH the 100-day AND the 200-day SMA (not just the 200-day alone) to
trigger an exit -- explicitly framed by the source as a false-signal
filter. Symmetrically, re-entry (Golden Cross variant) requires the 50-day
SMA to be back above BOTH the 100-day and 200-day SMA.

Distinct from this repo's existing SMA50/200 crossover variants (vol-gated
daily continuous re-evaluation in 2026-09-03_momentum_trend200_filter.py-
style strategies, and the separate monthly-decision-cadence Golden Cross
2026-09-11_monthly_golden_cross_regime.py) via being the first strategy in
this repo to use a THREE-moving-average simultaneous-confirmation trend
filter (50/100/200) rather than a simple two-MA crossover.

Signal logic
------------
- sma_fast (default 50), sma_mid (default 100), sma_slow (default 200) on
  the traded asset's own close.
- Long (in-position) when sma_fast > sma_mid AND sma_fast > sma_slow (both
  confirmations agree -- "Double Golden Cross").
- Flat when sma_fast < sma_mid AND sma_fast < sma_slow (both confirmations
  agree -- "Double Death Cross").
- Ambiguous zone (fast is between mid and slow, i.e. the two don't agree):
  HOLD prior state (this IS the false-signal filter -- a lone crossover of
  just one of the two slower MAs doesn't flip the position).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series (0/1 position)
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
    sma_fast: int = 50,
    sma_mid: int = 100,
    sma_slow: int = 200,
) -> pd.Series:
    """Return a {0,1} long/flat position series from the triple-SMA confirmation filter."""
    df = _prep(price_df)
    close = df["close"]

    fast = close.rolling(sma_fast, min_periods=sma_fast).mean()
    mid = close.rolling(sma_mid, min_periods=sma_mid).mean()
    slow = close.rolling(sma_slow, min_periods=sma_slow).mean()

    double_golden = (fast > mid) & (fast > slow)
    double_death = (fast < mid) & (fast < slow)

    valid = fast.notna() & mid.notna() & slow.notna()

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if not bool(valid.iloc[i]):
            position.iloc[i] = 0
            continue
        if bool(double_golden.iloc[i]):
            in_position = True
        elif bool(double_death.iloc[i]):
            in_position = False
        # else: ambiguous zone -- hold prior state (the false-signal filter)
        position.iloc[i] = int(in_position)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
