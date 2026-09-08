"""Strategy: Volume-Shock Gated Overnight Return.

Hypothesis (see knowledge_base/strategies_log.jsonl id TBD):
Per Cartea, Cucuringu, Jin & Wilson, "Volume Shocks and Overnight Returns"
(2025, Oxford; summarized at
https://www.quantitativo.com/p/volume-shocks-and-overnight-returns),
unexpected spikes in a stock's trading volume during the day predict
significantly higher CLOSE-TO-OPEN (overnight) returns -- but show no such
effect intraday (open-to-close). The paper's own oracle-portfolio test
(Table 1) sorts stocks into volume-shock deciles and holds the top decile
overnight only.

This repo already has an *unconditional* overnight-return-premium strategy
(2026-09-08-053, gated by a trend/SMA filter) and its weekend-effect
variant (2026-09-08-054, rejected). This iteration tests a DIFFERENT gate
on the same overnight-holding-period structure: instead of a trend filter,
gate the overnight hold on a VOLUME SHOCK signal -- only hold overnight
when today's volume is an outlier versus its own recent trailing
distribution (z-score above `vol_shock_threshold`), which is the paper's
actual mechanism, not a trend-following rationale. Adapted to daily OHLCV
(no intraday volume data available via our loaders), using the day's full
volume vs a rolling mean/std over `vol_window` days as the shock proxy.

Signal logic
------------
- Volume z-score at day t: (volume[t] - rolling_mean(vol_window)[t]) /
  rolling_std(vol_window)[t], computed using data known by day t's close.
- Position[t] = 1 (hold overnight into day t's open, entered at day t-1's
  close) iff volume z-score at t-1 > vol_shock_threshold; else 0.
- Overnight return for day t = open[t] / close[t-1] - 1, applied only when
  gated on.
- No intraday exposure at all (mirrors 2026-09-08-053's structure).

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
    vol_window: int = 20,
    vol_shock_threshold: float = 1.0,
) -> pd.Series:
    """Return a {0,1} series: 1 = holding overnight into this bar's open."""
    df = _prep(price_df)
    volume = df["volume"].astype(float)

    roll_mean = volume.rolling(vol_window).mean()
    roll_std = volume.rolling(vol_window).std()
    vol_zscore = (volume - roll_mean) / roll_std.replace(0, pd.NA)

    shock = vol_zscore > vol_shock_threshold
    # Decision to hold overnight INTO bar t is made using info known as of
    # the PRIOR close (t-1): shift the shock signal forward by 1 bar.
    position = shock.shift(1).fillna(False).astype(int)
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Overnight-only daily returns: open[t]/close[t-1] - 1, gated by volume shock."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]

    position = generate_signals(price_df, **kwargs)
    overnight_ret = (open_ / close.shift(1) - 1.0).fillna(0.0)
    strategy_ret = position * overnight_ret
    return strategy_ret
