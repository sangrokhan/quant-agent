"""Strategy: Bullish Mat Hold (5-candle continuation) + mid-vol regime gate,
RESCUED for crypto with a leverage-cap position-sizing dial (direct fix for
crypto near-miss 2026-09-18-051, which failed only on MDD).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-051 for
the mid-vol-gated Mat Hold construction this builds on):
The mid-vol-gated Bullish Mat Hold strategy (2026-09-18-051) was rejected on
equity (Sharpe flipped negative under the gate) but showed a genuine crypto
near-miss: ETH/USDT passed BOTH Sharpe (1.20 vs 1.0) and TC-survival (1.17
vs 0.5 net Sharpe after costs) outright, while BTC/USDT missed Sharpe only
narrowly (0.96 vs 1.0). The ONLY validator that failed on both crypto
symbols was max drawdown (BTC 30.4%, ETH 39.0%, both over the 25% cap) --
this is the classic pattern this cron trigger has repeatedly rescued
successfully via a leverage-cap position-sizing dial (PVO, Kairi, Williams
Alligator, Anchored Momentum, Ergodic Oscillator, Andean Oscillator, Ulcer
Index sizing dials earlier this same trigger cycle). This strategy applies
that exact same fix: scale every triggered Mat Hold position's exposure
down from 1.0 (full notional) to `leverage_cap` (e.g. 0.6), which reduces
both MDD and return volatility proportionally without touching the
already-working entry/exit signal logic on the crypto side.

Signal logic (identical mid-vol-gated Mat Hold pattern to 2026-09-18-051,
crypto-only, plus a leverage_cap sizing scalar)
------------------------------------------------------------------
- Same 5-candle Mat Hold structure + mid-vol regime gate at entry as
  2026-09-18-051.
- NEW: every triggered long position's exposure is `leverage_cap` (instead
  of a fixed 1.0), applied uniformly for the full holding period (unlike
  the continuous-sizing-dial rescues used elsewhere in this repo, this is a
  discrete-pattern strategy so a constant scalar during the hold is the
  natural analog).

Interface contract for validators/grid_test (see RESEARCH_LOOP.md Step 5):
    generate_signals(price_df, **params) -> pd.Series (continuous exposure
    in [0, leverage_cap])
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
    leverage_cap: float = 0.6,
) -> pd.Series:
    """Return a continuous exposure series in {0, leverage_cap}."""
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

    exposure = pd.Series(0.0, index=df.index, dtype=float)
    in_position = False
    entry_idx = 0
    stop_price = 0.0

    for i in range(4, n):
        if in_position:
            held = i - entry_idx
            if c[i] < stop_price or held >= max_hold_days:
                in_position = False
                exposure.iloc[i] = 0.0
                continue
            exposure.iloc[i] = leverage_cap
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
            exposure.iloc[i] = leverage_cap

    return exposure


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    exposure = generate_signals(price_df, **kwargs)
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = exposure.shift(1).fillna(0.0) * daily_ret
    return strategy_ret
