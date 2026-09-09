"""Strategy: PPO histogram pullback-reexpansion, 50-EMA trend-slope gated.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-09-069):
Per The Indicator Lab's PPO review (https://theindicatorlab.com/reviews/ppo-percentage-price-oscillator/,
browser_exec fallback -- web_extract cannot render this DDGS-backed
site, browser_exec used directly), the author's own preferred trading rule
is NOT a plain signal-line crossover: "Trend filter: Only take longs when
PPO is above zero and the 50 EMA is sloping up... Entry: Wait for a
pullback where the histogram shrinks toward zero but the PPO line stays
above the signal line. Enter on the first histogram expansion in the trend
direction... Exit: Trail with the 9 EMA or exit when the histogram crosses
below zero." This is distinct from this repo's existing
2026-09-04_ppo_signal_crossover_zeroline.py (id 2026-09-04-109), which
enters directly on the PPO/signal crossover itself with a zero-line filter
-- here the crossover must have ALREADY happened (PPO > signal, established
before the pullback) and the entry trigger is specifically the histogram's
first re-expansion after shrinking toward zero during a pullback, a
materially different (stricter) timing rule, analogous in spirit to this
same cron trigger's TRIX-pullback idea (2026-09-09-067, rejected) but
applied to the PPO histogram instead of the TRIX signal-line.

PPO formula (standard):
    ppo = 100 * (EMA(close, fast) - EMA(close, slow)) / EMA(close, slow)
    signal = EMA(ppo, signal_window)
    histogram = ppo - signal

Signal logic
------------
- Trend gate: ppo > 0 AND ema50 is sloping up (ema50 > ema50.shift(slope_lookback)).
- Pullback precondition: histogram shrank toward zero over the preceding
  `pullback_window` bars (abs(histogram) at t-1 < abs(histogram) at
  t-1-pullback_window) while ppo stayed above signal throughout (no bearish
  cross during the pullback).
- Entry (long): trend gate AND pullback precondition AND histogram expands
  today vs yesterday (|histogram_t| > |histogram_{t-1}|, i.e. "first
  histogram expansion") AND histogram > 0 (still on the bullish side).
- Exit: close crosses below its own `trail_ema_window`-period EMA (source's
  "trail with the 9 EMA"), OR histogram crosses below zero (bearish
  histogram flip), OR a `max_hold_days` time-stop (safety net, consistent
  with this repo's convention).
- Flat otherwise; long-only, no shorting (per SAFETY.md).

Interface contract for validators (see validation/validators.py):
    generate_signals(price_df, **params) -> pd.Series  (0/1 position)
    generate_returns(price_df, **params) -> pd.Series  (daily strategy returns)
Both accept tunable parameters as keyword arguments (grid_test.py calls
generate_returns_fn(price_df, **params) directly across a parameter grid).
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
    fast_window: int = 12,
    slow_window: int = 26,
    signal_window: int = 9,
    trend_ema_window: int = 50,
    trend_slope_lookback: int = 5,
    pullback_window: int = 6,
    trail_ema_window: int = 9,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    ema_fast = close.ewm(span=fast_window, adjust=False).mean()
    ema_slow = close.ewm(span=slow_window, adjust=False).mean()
    ppo = 100.0 * (ema_fast - ema_slow) / ema_slow
    signal = ppo.ewm(span=signal_window, adjust=False).mean()
    histogram = ppo - signal

    ema_trend = close.ewm(span=trend_ema_window, adjust=False).mean()
    trend_slope_up = ema_trend > ema_trend.shift(trend_slope_lookback)
    trend_gate = (ppo > 0) & trend_slope_up.fillna(False)

    ppo_above_signal = ppo > signal
    # PPO must have stayed above signal for the whole pullback window
    # (no bearish cross during the pullback).
    stayed_above = ppo_above_signal.rolling(pullback_window, min_periods=pullback_window).min().astype(bool)
    hist_abs = histogram.abs()
    pullback_shrink = hist_abs.shift(1) < hist_abs.shift(1 + pullback_window)
    pullback_precondition = stayed_above.shift(1).fillna(False) & pullback_shrink.fillna(False)

    hist_expanding = hist_abs > hist_abs.shift(1)
    bullish_hist = histogram > 0

    entry = trend_gate.fillna(False) & pullback_precondition & hist_expanding.fillna(False) & bullish_hist.fillna(False)

    ema_trail = close.ewm(span=trail_ema_window, adjust=False).mean()
    exit_trail = close < ema_trail
    exit_hist_flip = histogram < 0

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    for i in range(len(close)):
        if in_position:
            held = i - entry_idx
            if bool(exit_trail.iloc[i]) or bool(exit_hist_flip.iloc[i]) or held >= max_hold_days:
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
