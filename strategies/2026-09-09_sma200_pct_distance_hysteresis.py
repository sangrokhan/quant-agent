"""Strategy: 200-SMA percent-distance trend-following with QQQ-fallback
de-risk exit (long-only), adapted from the "SPY 200SMA +4%/-3%" LETF
rotation concept.

Hypothesis (this iteration):
Per a TradingView open-source script
(https://kr.tradingview.com/script/QEVAQHl6-SPY-200SMA-4-Entry-3-Exit-Strategy-QQQ-TQQQ/),
the underlying mechanical rule (stripped of its leveraged-ETF rotation
mechanics, which this repo's SAFETY.md/loaders.py don't support) is:
price crossing meaningfully ABOVE its 200-day SMA (source's own +4%
threshold, not simply close>SMA200) is a stronger, less-whipsaw-prone
trend-confirmation entry than a bare SMA crossover (already tested many
times in this repo, e.g. 2026-09-04-074), and exiting only once price
drops meaningfully BELOW the 200-SMA (source's own -3% threshold, again
not simply close<SMA200) avoids getting shaken out by minor SMA
undercuts during a still-intact uptrend. This creates an asymmetric
hysteresis band around the 200-SMA (source's own explicit design: distinct
non-symmetric entry/exit percentage offsets, +4% to enter vs -3% to exit)
distinct from every prior symmetric threshold-band strategy in this repo.

Distinct from the already-tested "standalone 200-day SMA price-position
rule" (2026-09-04-074, plain close>SMA(200) with NO percentage offset)
and every ADX/efficiency-ratio-gated 200-SMA variant (2026-09-05-071,
2026-09-08-002) since this uses PERCENTAGE DISTANCE from the SMA itself
(not a second momentum/regime indicator) as the sole entry/exit
mechanism, with deliberately asymmetric thresholds.

Signal logic
------------
- pct_above_sma = (close - SMA(sma_window)) / SMA(sma_window).
- Entry (long): pct_above_sma crosses above entry_pct_threshold (source's
  own +4% = 0.04).
- Exit: pct_above_sma drops below exit_pct_threshold (source's own -3% =
  -0.03, i.e. this is NOT "close < SMA", it requires being meaningfully
  BELOW the SMA) OR a max_hold_days time-stop backstop (source has no
  explicit time-stop, added per this repo's convention).

Interface contract for validators/grid_test (see validation/validators.py,
validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} long/flat)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)

Sources:
    https://kr.tradingview.com/script/QEVAQHl6-SPY-200SMA-4-Entry-3-Exit-Strategy-QQQ-TQQQ/
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
    sma_window: int = 200,
    entry_pct_threshold: float = 0.04,
    exit_pct_threshold: float = -0.03,
    max_hold_days: int = 250,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]
    n = len(close)

    sma = close.rolling(sma_window).mean()
    pct_above = (close - sma) / sma.replace(0, np.nan)

    entry_cross = (pct_above > entry_pct_threshold) & (pct_above.shift(1) <= entry_pct_threshold)
    exit_static = pct_above < exit_pct_threshold

    c = pct_above.to_numpy(dtype=float)
    entry_arr = entry_cross.fillna(False).to_numpy(dtype=bool)
    exit_arr = exit_static.fillna(True).to_numpy(dtype=bool)

    position = np.zeros(n, dtype=int)
    in_position = False
    entry_idx = 0

    for i in range(n):
        if in_position:
            held = i - entry_idx
            if exit_arr[i] or held >= max_hold_days:
                in_position = False
                position[i] = 0
                continue
            position[i] = 1
        else:
            if entry_arr[i]:
                in_position = True
                entry_idx = i
                position[i] = 1
            else:
                position[i] = 0

    return pd.Series(position, index=close.index, dtype=int)


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = (position.shift(1).fillna(0) * daily_ret)
    return strategy_ret
