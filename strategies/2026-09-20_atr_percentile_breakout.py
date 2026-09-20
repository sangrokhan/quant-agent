"""Strategy: ATR Percentile Breakout (volatility compression -> N-bar breakout).

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-20-125):
Source: https://pinescriptforge.com/strategy/atr-percentile-breakout
(visited via browser_exec this iteration; disclosed rule, backtested across
64 futures symbols on that site with per-symbol win-rate/profit-factor/
Sharpe figures).

Markets cycle between low and high volatility. When 14-period ATR falls
into the bottom decile of its own trailing 100-bar distribution, that
marks extreme compression -- the calm before an expansion move. Rather
than betting on direction, the strategy waits for price to actually break
a short (5-bar) high/low from that compressed state, treating the
breakout DIRECTION as the signal for which way volatility is about to
expand. Long-only adaptation (source is long/short symmetric; this repo's
generate_signals/generate_returns contract is long/flat).

This is distinct from every other volatility-compression-breakout entry
already in this repo:
- 2026-09-06-111 (Minervini VCP): requires a genuine multi-leg
  monotonically-shallowing swing-high/low pullback sequence + volume
  confirmation, far more structurally complex.
- 2026-09-08-004 / 2026-09-20-109 (TTM Squeeze): requires comparing TWO
  volatility bands (Bollinger vs Keltner) and a momentum histogram.
- 2026-09-08-023 / 2026-09-08-044 (Garman-Klass percentile): uses a
  different (OHLC-based) volatility estimator and a trend filter.
- 2026-09-18-080 (ATR-Percentile grid trading): a HIGH-ATR-percentile gate
  for a multi-order mean-reversion grid, the opposite regime and opposite
  technique (mean reversion, not breakout).
This strategy uses a single plain ATR-percentile gate (no trend filter, no
second volatility band, no multi-leg pattern) combined with a short 5-bar
high/low breakout entry and an ATR-multiple target/trail/failed-expansion
exit -- not previously tested in this exact combination.

Signal logic
------------
- ATR(atr_window) computed via Wilder's method (simple rolling mean of
  true range, matching this repo's existing ATR conventions elsewhere).
- atr_pctile = rolling percentile rank of current ATR within the trailing
  pctile_window bars.
- compressed = atr_pctile <= pctile_threshold (default 0.10 = bottom decile).
- Entry (long only): compressed was True within entry_lookback bars of the
  current bar (compression phase), AND today's close breaks above the
  breakout_window-bar high (excluding today).
- Exit: close >= entry_close + target_atr_mult * ATR(at entry) (target
  hit), OR close <= running_high - trail_atr_mult * ATR(at entry)
  (trailing stop), OR ATR contracts back into the bottom decile again
  within failed_expansion_bars of entry (failed breakout, source's
  "exit if ATR contracts again within 5 bars" rule), OR a max_hold_days
  time-stop backstop (not in source, added per this repo's convention to
  bound worst-case holding period).

Interface contract for validators (see validation/validators.py):
    generate_returns(price_df, **params) -> pd.Series
    generate_signals(price_df, **params) -> pd.Series ({0,1} long/flat)
"""

from __future__ import annotations

import pandas as pd


def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    df = price_df.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    df = df.sort_index()
    return df


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def generate_signals(
    price_df: pd.DataFrame,
    atr_window: int = 14,
    pctile_window: int = 100,
    pctile_threshold: float = 0.10,
    entry_lookback: int = 5,
    breakout_window: int = 5,
    target_atr_mult: float = 2.0,
    trail_atr_mult: float = 1.0,
    failed_expansion_bars: int = 5,
    max_hold_days: int = 20,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    close = df["close"]

    atr = _atr(df, atr_window)
    # Rolling percentile-rank of the current value within the trailing
    # window, vectorized via rank() (much faster than a Python-level
    # rolling.apply loop over 1000s of bars x grid cells).
    atr_pctile = atr.rolling(pctile_window).rank(pct=True)
    compressed = (atr_pctile <= pctile_threshold).fillna(False)
    was_compressed_recently = compressed.rolling(entry_lookback, min_periods=1).max().astype(bool)

    rolling_high = close.rolling(breakout_window).max().shift(1)
    breakout_up = close > rolling_high

    entry_signal = (was_compressed_recently & breakout_up).fillna(False)

    position = pd.Series(0, index=close.index, dtype=int)
    in_position = False
    entry_idx = 0
    entry_close = 0.0
    entry_atr = 0.0
    running_high = 0.0

    close_vals = close.values
    atr_vals = atr.values
    atr_pctile_vals = atr_pctile.values
    entry_signal_vals = entry_signal.values
    n = len(close_vals)

    for i in range(n):
        if in_position:
            held = i - entry_idx
            running_high = max(running_high, close_vals[i])
            target_hit = close_vals[i] >= entry_close + target_atr_mult * entry_atr
            trail_hit = close_vals[i] <= running_high - trail_atr_mult * entry_atr
            failed_expansion = (
                held <= failed_expansion_bars
                and not pd.isna(atr_pctile_vals[i])
                and atr_pctile_vals[i] <= pctile_threshold
                and held > 0
            )
            time_stop = held >= max_hold_days
            if target_hit or trail_hit or failed_expansion or time_stop:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            if bool(entry_signal_vals[i]) and not pd.isna(atr_vals[i]):
                in_position = True
                entry_idx = i
                entry_close = close_vals[i]
                entry_atr = atr_vals[i]
                running_high = close_vals[i]
                position.iloc[i] = 1
            else:
                position.iloc[i] = 0
    return position


def generate_returns(price_df: pd.DataFrame, **kwargs) -> pd.Series:
    """Position-weighted daily returns (no transaction costs)."""
    df = _prep(price_df)
    close = df["close"]
    position = generate_signals(price_df, **kwargs)
    # Shift position by 1 day: yesterday's signal determines today's return
    # exposure (avoid look-ahead bias -- can't trade on today's own close).
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position.shift(1).fillna(0) * daily_ret
    return strategy_ret
