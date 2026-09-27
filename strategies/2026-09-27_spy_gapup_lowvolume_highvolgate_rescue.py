"""Strategy: SPY-style gap-up-after-low-volume intraday momentum, rescued
with a HIGH-volatility-regime gate.

Hypothesis (2026-09-27 KB entry, this iteration): direct rescue of this same
cron trigger's own near-miss 2026-09-27-068 (SPY-style gap-up-after-low-
volume intraday momentum -- per
https://www.quantifiedstrategies.com/spy-volume-trading-strategy/ -- SPY
Sharpe 0.731, QQQ Sharpe 0.720, both failing the 1.0 threshold). That
entry's grid test showed the edge concentrated ENTIRELY in the high-vol
tercile (10/24 passing cells all in "high", zero in "low"/"mid") -- the
INVERSE pattern from the repo's usual low-vol-gate rescue playbook (e.g.
SILJ/SIL 2026-09-27-064, GDXJ/GDX 2026-09-27-065). This iteration adds an
explicit high-realized-vol regime gate (trade only when trailing realized
vol >= rv_min_ratio x its trailing median) on top of the same gap-up/
low-volume signal, hypothesizing that isolating the regime where the edge
actually lives (rather than diluting it across the full unconditional
sample) clears the Sharpe bar. Same underlying gap/volume mechanism and
data as 2026-09-27-068; the only change is this added regime filter.

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def generate_signals(
    price_df: pd.DataFrame,
    vol_avg_window: int = 15,
    min_gap_pct: float = 0.006,
    rv_window: int = 20,
    rv_lookback: int = 252,
    rv_min_ratio: float = 1.5,
) -> pd.Series:
    """Return a {0,1} indicator: 1 = trade today's open-to-close session
    (previous day's TRADING volume was below its own trailing average AND
    today's open gaps up from yesterday's close by >= min_gap_pct AND
    trailing rv_window-day realized vol is >= rv_min_ratio x its trailing
    rv_lookback-day median, i.e. an elevated/high-volatility regime); 0 =
    flat otherwise.
    """
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    volume = df["volume"]

    vol_avg = volume.rolling(vol_avg_window).mean()
    prev_day_low_volume = (volume.shift(1) < vol_avg.shift(1)).fillna(False)

    gap_pct = (open_ / close.shift(1)) - 1.0
    big_gap_up = (gap_pct >= min_gap_pct).fillna(False)

    daily_log_ret = np.log(close / close.shift(1))
    realized_vol = daily_log_ret.rolling(rv_window).std()
    vol_median = realized_vol.rolling(rv_lookback, min_periods=rv_window).median()
    high_vol_regime = (realized_vol >= (vol_median * rv_min_ratio)).fillna(False)

    signal = (prev_day_low_volume & big_gap_up & high_vol_regime).astype(int)
    return signal


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Open-to-close return on flagged days, 0 elsewhere (no transaction
    costs applied here)."""
    df = _prep(price_df)
    close = df["close"]
    open_ = df["open"]
    intraday_ret = (close / open_) - 1.0

    signal = generate_signals(price_df, **kwargs)
    strat_ret = intraday_ret * signal
    return strat_ret.fillna(0.0)
