"""Strategy: DTI (Directional Trend Index) zero-line crossover, high-vol-regime gated.

Direct fix attempt for this cron trigger's own prior near-miss rejection
(2026-09-22-023, ungated DTI zero-line crossover): QQQ failed only on
Sharpe near-miss (0.962 vs 1.0 threshold) and MDD (0.282 vs 0.25 threshold)
at the grid-best config (r=20, max_hold_days=20), while SPY passed cleanly.
That entry's own Step 6 grid showed the high-vol regime tercile decisively
fails (0/36 pass) across ALL symbols/configs -- the strategy is a
trend-following signal that whipsaws during high-vol regimes. This
iteration adds an explicit realized-vol regime gate (flatten whenever
trailing 20d realized vol exceeds its trailing 252d median by
vol_regime_ratio) on TOP of the identical unmodified DTI entry/exit logic,
following this repo's established binary-rescue pattern (see e.g.
2026-09-03_bb_meanrev_qqq_volregime.py, 2026-09-09-089, 2026-09-17-060).

Source: https://www.mql5.com/en/code/384, https://www.mql5.com/en/code/382
(unchanged from 2026-09-22-023).

Signal logic
------------
- 20-day realized volatility (annualized std of daily log returns) vs its
  trailing 252-day median -> "low/mid-vol regime" when current 20d vol
  <= vol_regime_ratio * that median.
- Entry (long): DTI crosses from <=0 to >0 AND we are in a low/mid-vol
  regime.
- Exit: DTI crosses back to <=0, OR the vol regime flips to high-vol
  (risk-off exit), OR a max_hold_days time-stop.

Interface contract for validators (see validation/validators.py) and the
grid tester (see validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series   ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
"""

from __future__ import annotations

import math

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _triple_ema(series: pd.Series, r: int, s: int, u: int) -> pd.Series:
    e1 = series.ewm(span=r, min_periods=r, adjust=False).mean()
    e2 = e1.ewm(span=s, min_periods=s, adjust=False).mean()
    e3 = e2.ewm(span=u, min_periods=u, adjust=False).mean()
    return e3


def _dti(
    high: pd.Series,
    low: pd.Series,
    q: int = 2,
    r: int = 20,
    s: int = 5,
    u: int = 3,
) -> pd.Series:
    hmu = (high - high.shift(q - 1)).clip(lower=0.0)
    lmd = (-(low - low.shift(q - 1))).clip(lower=0.0)
    hlm = hmu - lmd

    smoothed_hlm = _triple_ema(hlm, r, s, u)
    smoothed_abs_hlm = _triple_ema(hlm.abs(), r, s, u)

    dti = 100.0 * smoothed_hlm / smoothed_abs_hlm.replace(0.0, 1e-12)
    return dti


def generate_signals(
    price_df: pd.DataFrame,
    q: int = 2,
    r: int = 20,
    s: int = 5,
    u: int = 3,
    max_hold_days: int = 20,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_ratio: float = 1.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series, gated by a vol regime filter."""
    df = _prep(price_df)
    high = df["high"]
    low = df["low"]
    close = df["close"]

    ratios = close / close.shift(1)
    daily_log_ret = ratios.apply(lambda x: math.log(x) if x and x > 0 else None).astype(float)
    realized_vol = daily_log_ret.rolling(vol_window).std() * (252 ** 0.5)
    vol_median_1y = realized_vol.rolling(vol_lookback, min_periods=vol_window).median()
    low_mid_vol_regime = (realized_vol <= (vol_median_1y * vol_regime_ratio)).fillna(False)

    dti = _dti(high, low, q, r, s, u)
    above_zero = dti > 0
    cross_up = above_zero & ~above_zero.shift(1).fillna(False)
    cross_down = (~above_zero) & above_zero.shift(1).fillna(False)

    entry_trigger = cross_up & low_mid_vol_regime
    exit_regime_flip = ~low_mid_vol_regime

    position = pd.Series(0, index=high.index, dtype=int)
    in_position = False
    entry_idx = 0
    n = len(high)
    for i in range(n):
        if in_position:
            held = i - entry_idx
            if bool(cross_down.iloc[i]) or bool(exit_regime_flip.iloc[i]) or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_trigger.iloc[i]):
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
