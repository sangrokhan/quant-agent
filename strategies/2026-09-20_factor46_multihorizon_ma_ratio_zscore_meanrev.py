"""Strategy: Factor46 Multi-Horizon MA-Ratio Mean Reversion (single-asset
time-series z-score adaptation of a cross-sectional stat-arb factor).

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD):
Per Quantitativo's "Modern Statistical Arbitrage"
(https://www.quantitativo.com/p/modern-statistical-arbitrage), building on
"The Modern Spirit of Statistical Arbitrage" (SysLS) and a paper testing
190+ cross-sectional equity factors: "Factor 46" (the paper's own
numbering), the paper's Multi-Period Mean Reversion Ratio, is defined as

    factor46 = (MEAN(CLOSE, 3) + MEAN(CLOSE, 6) + MEAN(CLOSE, 12)
                + MEAN(CLOSE, 24)) / (4 * CLOSE)

i.e. four trailing simple moving averages (3, 6, 12, 24 days -- each
window roughly doubling, spanning a few days to about a trading month),
equal-weighted into one blended reference price, divided by today's close.
A value > 1 means price sits BELOW its own recent multi-horizon average
(a recent sell-off relative to its own recent path); a value < 1 means it
sits above (a recent run-up). The source's own economic rationale: the
effect is short-horizon cross-sectional mean reversion / contrarian price
correction, grounded in overreaction/herding/liquidity-seeking behavioral
universality, persisting because arbitrageurs are slow to close the gap
(noise-trader risk / limits to arbitrage). Source's own cross-sectional
single-factor backtest: Sharpe 0.53 (S&P 500, worst) to 1.46 (S&P/ASX 300,
best), with the S&P 500 version alone suffering a 55.7% drawdown -- the
source's own conclusion is that ONE signal alone is not tradeable and
needs to be combined with 16 others into a diversified portfolio.

This repo's data/loaders.py is single-symbol, so the cross-sectional
"distance from the basket average, then long the laggards / short the
leaders" construction cannot be replicated as-is. Adapted here (following
this repo's established cross-sectional-to-time-series adaptation pattern,
e.g. 2026-09-09-112's skewness adaptation) as a single-asset TIME-SERIES
z-score: entry when the asset's OWN factor46 value is an unusually large
number of its own trailing standard deviations above its own trailing mean
(i.e. abnormally far below its own multi-horizon blended average relative
to its own history), long, exit on reversion toward the mean or a
time-stop. This is a genuinely distinct construction from this repo's
existing Disparity Index strategies (2026-09-06-140/2026-09-18-130), which
use a SINGLE SMA's raw percent-distance -- factor46 blends FOUR different-
window moving averages into one ratio before z-scoring, and is entered on
absolute value of that blended ratio rather than percent-distance from one
MA.

Interface contract for validators (see validation/validators.py) and the
grid tester (validation/grid_test.py) -- both generate_signals and
generate_returns accept all tunable parameters as keyword arguments.
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
    z_window: int = 252,
    entry_z: float = 1.5,
    exit_z: float = 0.0,
    max_hold_days: int = 10,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ma3 = close.rolling(3).mean()
    ma6 = close.rolling(6).mean()
    ma12 = close.rolling(12).mean()
    ma24 = close.rolling(24).mean()
    factor46 = (ma3 + ma6 + ma12 + ma24) / (4 * close)

    rolling_mean = factor46.rolling(z_window, min_periods=max(30, z_window // 4)).mean()
    rolling_std = factor46.rolling(z_window, min_periods=max(30, z_window // 4)).std()
    z = (factor46 - rolling_mean) / rolling_std.replace(0, pd.NA)

    entry = (z >= entry_z).fillna(False)
    exit_reversion = (z <= exit_z).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_reversion.iloc[i]) or held >= max_hold_days:
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
