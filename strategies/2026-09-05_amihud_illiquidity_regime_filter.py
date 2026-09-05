"""Strategy: Amihud illiquidity-spike regime filter (liquidity timing).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-05-027):
Per Amihud (2002) and the summary at
https://microalphas.com/amihud-illiquidity/, aggregate/security-level
illiquidity (ILLIQ = mean(|daily return| / dollar volume) over a rolling
window) rising sharply signals market stress: "rising illiquidity has
historically accompanied stress and drawdowns." This is a distinct,
single-asset, price+volume-only signal not previously tested in this repo
(no prior entries for "Amihud"/"illiquidity" in strategies_index.jsonl).

Signal logic
------------
- Daily Amihud ILLIQ = |daily return| / dollar_volume (price * volume),
  scaled by 1e6 for numerical readability (cosmetic only, per source).
- Rolling illiq_window-day average of daily ILLIQ.
- z-score of that rolling average vs its own trailing illiq_lookback-day
  history (mean/std).
- Risk-off (flat) when z-score >= risk_off_z (illiquidity spiking well
  above its recent norm); long otherwise (default long-biased, since ILLIQ
  spikes are the rare/informative event, not steady-state).
- No look-ahead: position uses only data available at the end of the
  signal day; generate_returns shifts by 1 day before applying returns.

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
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
    illiq_window: int = 20,
    illiq_lookback: int = 252,
    risk_off_z: float = 2.0,
) -> pd.Series:
    """Return a {0,1} long/flat position series.

    Flat whenever rolling Amihud illiquidity z-score >= risk_off_z
    (illiquidity spiking), long otherwise.
    """
    df = _prep(price_df)
    close = df["close"]
    volume = df["volume"]

    daily_ret = close.pct_change()
    dollar_volume = (close * volume).replace(0, np.nan)

    daily_illiq = (daily_ret.abs() / dollar_volume) * 1_000_000
    rolling_illiq = daily_illiq.rolling(illiq_window, min_periods=illiq_window).mean()

    roll_mean = rolling_illiq.rolling(illiq_lookback, min_periods=illiq_window).mean()
    roll_std = rolling_illiq.rolling(illiq_lookback, min_periods=illiq_window).std()
    zscore = (rolling_illiq - roll_mean) / roll_std.replace(0, np.nan)

    risk_off = (zscore >= risk_off_z).fillna(False)
    position = (~risk_off).astype(int)
    # Before any data is available for the rolling windows, stay flat.
    warmup_mask = rolling_illiq.isna() | roll_std.isna()
    position[warmup_mask] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
