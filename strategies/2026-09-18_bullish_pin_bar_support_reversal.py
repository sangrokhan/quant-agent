"""Strategy: Bullish pin bar ("Pinocchio bar") reversal at rolling support,
with an ATR-buffered stop and a fixed risk:reward profit target.

Hypothesis (see knowledge_base/strategies_log.jsonl id=2026-09-18-021):
Per tradingstrategyguides.com's "Pin Bar Reversal Strategy: The Complete
Guide For Price Action Traders" (visited this iteration), a genuine bullish
pin bar requires (a) a lower tail/wick that is at least ~2-3x the real body
and accounts for the large majority of the candle's total range, (b) a small
or non-existent upper "nose" wick (<=15% of range), (c) the real body closing
within the top 25% of the candle's range, and critically (d) the pattern
must occur at a "key support level" -- the source explicitly states pin bars
"traded in isolation fail" and must form at established support/resistance.
This strategy operationalizes (d) with a purely price-based rolling support
proxy (today's low sits at/near the trailing N-day rolling minimum low),
since the repo's OHLCV loaders don't carry discretionary trendline/S&R
annotations. Long entry the day after a qualifying bullish pin bar forms at
rolling support; exit at a fixed risk:reward profit target (source
recommends >=2:1) measured off the pin bar's own tail-implied stop distance,
a hard stop-loss below the tail tip, or a max holding period time-stop.

First candlestick-pattern-at-support strategy in this repo requiring the
'at a level' confluence condition explicitly (distinct from other single-
candle patterns like bullish engulfing/hammer/doji tested previously without
a support-proximity gate).

Interface contract (see validation/validators.py / validation/grid_test.py):
    generate_signals(price_df, **params) -> pd.Series  ({0,1} position)
    generate_returns(price_df, **params) -> pd.Series   (daily strategy returns)
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
    support_lookback: int = 20,
    support_tolerance: float = 0.01,   # today's low must be within 1% of the rolling min low
    min_tail_body_ratio: float = 2.0,  # lower tail >= 2x real body
    max_nose_pct: float = 0.15,        # upper wick <= 15% of total range
    min_body_top_pct: float = 0.75,    # body's low edge must sit in the top 25% of the range
    rr_target: float = 2.0,            # profit target = rr_target * (entry - stop) risk
    stop_buffer_pct: float = 0.002,    # stop placed stop_buffer_pct below the pin bar's low
    max_hold_days: int = 15,
) -> pd.Series:
    """Return a {0,1} long/flat position series."""
    df = _prep(price_df)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]

    rng = (h - l).replace(0, pd.NA)
    body_top = pd.concat([o, c], axis=1).max(axis=1)
    body_bot = pd.concat([o, c], axis=1).min(axis=1)
    body = (body_top - body_bot)
    lower_tail = (body_bot - l)
    upper_nose = (h - body_top)

    rolling_min_low = l.rolling(support_lookback).min()
    at_support = l <= rolling_min_low * (1.0 + support_tolerance)

    tail_ok = (body > 0) & (lower_tail >= min_tail_body_ratio * body)
    # allow doji-like zero-body candles with a dominant tail too
    tail_ok = tail_ok | ((body <= 1e-9) & (lower_tail > 0) & (rng > 0))
    nose_ok = (upper_nose / rng).fillna(1.0) <= max_nose_pct
    body_pos_ok = ((body_bot - l) / rng).fillna(0.0) >= min_body_top_pct

    bullish_pin_bar = tail_ok & nose_ok & body_pos_ok & at_support.fillna(False) & (rng > 0)

    position = pd.Series(0, index=c.index, dtype=int)
    in_position = False
    entry_idx = 0
    stop_price = 0.0
    target_price = 0.0

    idx = c.index
    n = len(idx)
    for i in range(n):
        if in_position:
            held = i - entry_idx
            hit_stop = bool(l.iloc[i] <= stop_price)
            hit_target = bool(h.iloc[i] >= target_price)
            if hit_stop or hit_target or held >= max_hold_days:
                in_position = False
                position.iloc[i] = 0
                continue
            position.iloc[i] = 1
        else:
            # Signal formed on bar i-1 (yesterday); enter today.
            if i > 0 and bool(bullish_pin_bar.iloc[i - 1]):
                pin_low = float(l.iloc[i - 1])
                pin_stop = pin_low * (1.0 - stop_buffer_pct)
                entry_price = float(o.iloc[i]) if not pd.isna(o.iloc[i]) else float(c.iloc[i - 1])
                risk = entry_price - pin_stop
                if risk > 0:
                    stop_price = pin_stop
                    target_price = entry_price + rr_target * risk
                    in_position = True
                    entry_idx = i
                    position.iloc[i] = 1
                    continue
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
