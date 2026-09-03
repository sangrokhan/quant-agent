"""Strategy: Vortex Indicator (VI+/VI-) crossover, SMA-trend-filtered.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-04-040):
Per Google AI-overview + multiple TA sources (PyQuantLab/Medium,
Capital.com, Enlightened Stock Trading): the Vortex Indicator (VI+/VI-,
standard 14-period) crossing -- VI+ crossing above VI- signals the start
of an uptrend -- gated by a trend/regime filter (close above a 50 or
200-day SMA) to avoid whipsaws in choppy/sideways markets, per multiple
sources' explicit warning that the raw crossover underperforms without
such a filter. Exit on the opposing crossover (VI- crosses above VI+).
Long-only, per repo convention.

Vortex Indicator formula (standard params, window=14):
    VM+ = abs(high - low.shift(1))        # positive vortex movement
    VM- = abs(low - high.shift(1))        # negative vortex movement
    TR  = max(high-low, abs(high-close.shift(1)), abs(low-close.shift(1)))  # true range
    VI+ = sum(VM+, window) / sum(TR, window)
    VI- = sum(VM-, window) / sum(TR, window)

Signal logic
------------
- Entry (long): VI+ crosses above VI- (fresh cross, not every bar VI+
  stays above) AND close > SMA(trend_window) (regime filter).
- Exit: VI- crosses above VI+.
- Flat otherwise; long-only, no shorting.

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


def _vortex(df: pd.DataFrame, window: int) -> tuple[pd.Series, pd.Series]:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)

    vm_plus = (high - low.shift(1)).abs()
    vm_minus = (low - high.shift(1)).abs()

    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    tr_sum = tr.rolling(window).sum()
    vi_plus = vm_plus.rolling(window).sum() / tr_sum
    vi_minus = vm_minus.rolling(window).sum() / tr_sum
    return vi_plus, vi_minus


def generate_signals(
    price_df: pd.DataFrame,
    vortex_window: int = 14,
    trend_window: int = 50,
) -> pd.Series:
    # Defaults (vortex_window=14, trend_window=50) are the grid/validator-
    # selected primary config for QQQ (see
    # backtests/2026-09-04_vortex_crossover_trend.md) -- notably NOT the
    # grid's naive best_cell by low-vol-tercile Sharpe (vortex_window=21,
    # trend_window=200), which underperforms on the full sample.
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    vi_plus, vi_minus = _vortex(df, vortex_window)
    sma_trend = close.rolling(trend_window).mean()

    bullish_cross = (vi_plus > vi_minus) & (vi_plus.shift(1) <= vi_minus.shift(1))
    bearish_cross = (vi_minus > vi_plus) & (vi_minus.shift(1) <= vi_plus.shift(1))

    entry = bullish_cross & (close > sma_trend).fillna(False)
    exit_signal = bearish_cross

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    for i in range(len(close)):
        if in_position:
            if bool(exit_signal.iloc[i]):
                in_position = False
                position.iloc[i] = 0
            else:
                position.iloc[i] = 1
        else:
            if bool(entry.iloc[i]):
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
