"""Strategy: Bullish Mat Hold (5-candle continuation), RESCUED with an
explicit MID-VOLATILITY REGIME GATE (direct fix for near-miss 2026-09-09-035).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-035 for the
original pattern construction and its rejection):
The original Bullish Mat Hold strategy (strategies/2026-09-09_bullish_mat_hold.py)
was rejected on full-sample Sharpe (QQQ 0.616, SPY 0.498, both below the 1.0
threshold), but its own grid-test breakdown showed the edge was concentrated
almost entirely in the MID-volatility tercile: "Grid ... 13/72 cells passed
(equity 13/36, crypto 0/36 decisive; low-vol 5/24, mid-vol 8/24, high-vol
0/24) ... best cell Sharpe 1.90 ... concentrated in mid-vol tercile only
(0/24 high-vol) ... future revisit could gate on mid-vol regime
specifically." This strategy is that direct rescue: add an explicit
mid-volatility regime gate (20-day realized vol between a lower and upper
band of its own trailing 252-day median) so entries are only taken when the
market is in the "goldilocks" mid-vol regime where the pattern's edge
actually lives, rather than trading it unconditionally through low-vol
(too quiet, pattern noise dominates) and high-vol (too choppy, structural
consolidation requirement gets violated) regimes where it decisively fails.

Signal logic (identical 5-candle Mat Hold structure to 2026-09-09-035, plus
the new mid-vol regime gate)
------------------------------------------------------------------
- Same candle 1 (strong bullish impulse) / candles 2-4 (consolidation
  holding above candle 1's low) / candle 5 (bullish breakout above candle
  1's high) pattern as the original.
- NEW: 20-day realized volatility (annualized std of daily log returns) vs
  its trailing 252-day median must fall within [vol_regime_low_ratio,
  vol_regime_high_ratio] x that median at candle 5 (the entry bar) --
  "mid-vol regime" gate. Entries outside this band are skipped entirely.
- Exit: unchanged (close crosses back below candle 1's low, or max_hold_days
  time-stop) -- NOT additionally gated by the vol regime on exit, since the
  entry-only gate is what the original near-miss notes specifically flagged.

Interface contract for validators/grid_test (see RESEARCH_LOOP.md Step 5):
    generate_signals(price_df, **params) -> pd.Series ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series (daily strategy returns)
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _mid_vol_regime(
    close: pd.Series,
    vol_window: int,
    vol_lookback: int,
    vol_regime_low_ratio: float,
    vol_regime_high_ratio: float,
) -> pd.Series:
    log_ret = np.log(close).diff()
    realized_vol = log_ret.rolling(vol_window).std() * math.sqrt(252)
    trailing_median = realized_vol.rolling(vol_lookback, min_periods=max(20, vol_lookback // 4)).median()
    mid_vol = (realized_vol >= vol_regime_low_ratio * trailing_median) & (
        realized_vol <= vol_regime_high_ratio * trailing_median
    )
    return mid_vol.fillna(False)


def generate_signals(
    price_df: pd.DataFrame,
    trend_window: int = 50,
    body_lookback: int = 20,
    impulse_body_mult: float = 1.3,
    consolidation_tolerance: float = 0.01,
    max_hold_days: int = 15,
    vol_window: int = 20,
    vol_lookback: int = 252,
    vol_regime_low_ratio: float = 0.75,
    vol_regime_high_ratio: float = 1.5,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    open_, high, low, close = df["open"], df["high"], df["low"], df["close"]
    trend_sma = close.rolling(trend_window, min_periods=trend_window).mean()
    real_body = (close - open_).abs()
    avg_body = real_body.rolling(body_lookback, min_periods=body_lookback).mean()
    mid_vol = _mid_vol_regime(close, vol_window, vol_lookback, vol_regime_low_ratio, vol_regime_high_ratio)

    n = len(df)
    o = open_.values
    h = high.values
    l = low.values
    c = close.values
    sma = trend_sma.values
    ab = avg_body.values
    mv = mid_vol.values

    position = pd.Series(0, index=df.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_price = 0.0

    for i in range(4, n):
        if in_position:
            held = i - entry_idx
            if c[i] < stop_price or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
            continue

        i1 = i - 4  # candle 1
        if pd.isna(sma[i1]) or pd.isna(ab[i1]) or ab[i1] <= 0:
            continue
        if not bool(mv[i]):
            continue

        c1_bullish = c[i1] > o[i1]
        c1_body = abs(c[i1] - o[i1])
        c1_strong = c1_body >= impulse_body_mult * ab[i1]
        uptrend = c[i1] > sma[i1]

        c1_low = l[i1]
        c1_high = h[i1]

        consolidation_holds = all(
            l[j] >= c1_low * (1 - consolidation_tolerance) for j in (i - 3, i - 2, i - 1)
        )

        c5_bullish = c[i] > o[i]
        c5_breakout = c[i] > c1_high

        if c1_bullish and c1_strong and uptrend and consolidation_holds and c5_bullish and c5_breakout:
            in_position = True
            entry_idx = i
            stop_price = c1_low
            position.iloc[i] = 1

    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
