"""Strategy: Volatility Contraction Pattern (VCP, Mark Minervini) breakout.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-06-111),
sourced from https://www.luxalgo.com/library/indicator/volatility-contraction-pattern/
(LuxAlgo "Volatility Contraction Pattern" indicator page): "Volatility
Contraction Pattern scans for Mark Minervini's tightening base: successive
pullbacks, each meaningfully shallower than the last, volume drying up into
the final coil, all inside a qualified uptrend... Pivot breakout: a close
through the pivot on clear volume expansion completes the pattern." Default
settings disclosed: Swing Length=5, Contractions=2-4, Max Depth Ratio=0.75
(each pullback at most 0.75x the prior pullback's depth), uptrend qualifier
via Trend SMA(200) + 52-week-range position (within 25% below the yearly
high, at least 30% above the yearly low), Volume Average Length=50,
Breakout Volume Multiplier=1.5.

First VCP-family strategy in this repo. Distinct from every prior breakout
strategy tested (Donchian, Darvas Box, ATR-expansion, TTM Squeeze, Bollinger
Bandwidth squeeze) because VCP specifically requires a MULTI-CONTRACTION
sequence of monotonically shallower pullbacks (not a single volatility
compression reading) confirmed by a volume-dry-up-then-expansion signature.

Signal logic (mechanical simplification of the source's full pattern-scan
for tractable daily-bar backtesting)
------------------------------------------------------------------
- Swing pivots: a local high/low over a `swing_length`-bar window on each
  side (simple fractal-style pivot detection).
- Pullback depth: % drop from a swing high to the following swing low.
- Tightening sequence: the most recent `contractions` pullback depths must
  each be <= `max_depth_ratio` times the prior pullback's depth (monotonic
  shallowing).
- Uptrend qualifier: close > SMA(trend_sma_window) (simplified from the
  source's fuller 52-week-range criteria).
- Volume dry-up: average volume during the final contraction period below
  its own `vol_avg_window`-day average (Volume Average Length).
- Entry: close breaks above the final contraction's swing-high pivot AND
  volume on the breakout bar >= `breakout_vol_mult` * `vol_avg_window`-day
  average volume.
- Exit: close falls back below the final contraction's swing low (source's
  own stop-discipline rule: "risk is defined under the final contraction
  low"), or a `max_hold_days` time-stop.

Interface contract for validators (see validation/validators.py) and
grid_test.py:
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position series)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy
        returns, position lagged by 1 day to avoid look-ahead bias)
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


def _find_pivots(high: np.ndarray, low: np.ndarray, swing_length: int):
    n = len(high)
    pivot_high = np.zeros(n, dtype=bool)
    pivot_low = np.zeros(n, dtype=bool)
    for i in range(swing_length, n - swing_length):
        window_h = high[i - swing_length : i + swing_length + 1]
        window_l = low[i - swing_length : i + swing_length + 1]
        if high[i] == window_h.max():
            pivot_high[i] = True
        if low[i] == window_l.min():
            pivot_low[i] = True
    return pivot_high, pivot_low


def generate_signals(
    price_df: pd.DataFrame,
    swing_length: int = 5,
    contractions: int = 2,
    max_depth_ratio: float = 0.75,
    trend_sma_window: int = 200,
    vol_avg_window: int = 50,
    breakout_vol_mult: float = 1.5,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"].values
    high = df["high"].values if "high" in df.columns else close
    low = df["low"].values if "low" in df.columns else close
    volume = df["volume"].values if "volume" in df.columns else np.ones(len(df))
    n = len(df)

    trend_sma = df["close"].rolling(trend_sma_window, min_periods=trend_sma_window).mean().values
    vol_avg = pd.Series(volume, index=df.index).rolling(vol_avg_window, min_periods=vol_avg_window).mean().values

    pivot_high, pivot_low = _find_pivots(high, low, swing_length)
    pivot_high_idx = np.where(pivot_high)[0]
    pivot_low_idx = np.where(pivot_low)[0]

    position = np.zeros(n, dtype=int)
    in_pos = False
    hold_count = 0
    active_stop_low = None
    active_pivot_price = None

    for i in range(n):
        if in_pos:
            hold_count += 1
            if (close[i] < active_stop_low) or (hold_count >= max_hold_days):
                in_pos = False
            position[i] = 1 if in_pos else 0
            continue

        # Build the alternating pivot-high/pivot-low sequence up to bar i.
        highs_before = pivot_high_idx[pivot_high_idx <= i]
        lows_before = pivot_low_idx[pivot_low_idx <= i]
        if len(highs_before) < contractions + 1 or len(lows_before) < contractions:
            position[i] = 0
            continue

        # Take the most recent (contractions+1) highs and contractions lows,
        # interleaved as high[0] -> low[0] -> high[1] -> low[1] -> ... to
        # form `contractions` pullback legs, each high[k]->low[k].
        recent_highs = highs_before[-(contractions + 1):]
        recent_lows = lows_before[-contractions:]

        # Require alternation: each low must fall strictly between its
        # corresponding high and the next high (simple sanity check).
        valid_sequence = True
        depths = []
        for k in range(contractions):
            h_idx = recent_highs[k]
            l_idx = recent_lows[k]
            if not (h_idx < l_idx):
                valid_sequence = False
                break
            depth = (high[h_idx] - low[l_idx]) / high[h_idx] if high[h_idx] > 0 else 0.0
            depths.append(depth)

        if not valid_sequence or len(depths) < contractions:
            position[i] = 0
            continue

        # Tightening check: each successive depth <= max_depth_ratio * prior.
        tightening = all(
            depths[k] <= max_depth_ratio * depths[k - 1] for k in range(1, len(depths))
        )
        if not tightening:
            position[i] = 0
            continue

        final_high_idx = recent_highs[-1]
        final_low_idx = recent_lows[-1]
        pivot_price = high[final_high_idx]
        stop_price = low[final_low_idx]

        if np.isnan(trend_sma[i]) or close[i] <= trend_sma[i]:
            position[i] = 0
            continue

        if np.isnan(vol_avg[i]):
            position[i] = 0
            continue

        # Volume dry-up during the final contraction (low[..] to now).
        contraction_vol = volume[final_low_idx : i + 1]
        if len(contraction_vol) == 0 or contraction_vol.mean() >= vol_avg[i]:
            position[i] = 0
            continue

        # Breakout: close above the pivot with volume expansion.
        if close[i] > pivot_price and volume[i] >= breakout_vol_mult * vol_avg[i]:
            in_pos = True
            hold_count = 0
            active_stop_low = stop_price
            active_pivot_price = pivot_price
            position[i] = 1
        else:
            position[i] = 0

    return pd.Series(position, index=df.index, name="position")


def generate_returns(
    price_df: pd.DataFrame,
    swing_length: int = 5,
    contractions: int = 2,
    max_depth_ratio: float = 0.75,
    trend_sma_window: int = 200,
    vol_avg_window: int = 50,
    breakout_vol_mult: float = 1.5,
    max_hold_days: int = 40,
) -> pd.Series:
    """Return daily strategy returns, position lagged by 1 day (no look-ahead)."""
    df = _prep(price_df)
    position = generate_signals(
        df,
        swing_length=swing_length,
        contractions=contractions,
        max_depth_ratio=max_depth_ratio,
        trend_sma_window=trend_sma_window,
        vol_avg_window=vol_avg_window,
        breakout_vol_mult=breakout_vol_mult,
        max_hold_days=max_hold_days,
    )
    daily_returns = df["close"].pct_change().fillna(0.0)
    strat_returns = position.shift(1).fillna(0) * daily_returns
    strat_returns.name = "strategy_returns"
    return strat_returns
